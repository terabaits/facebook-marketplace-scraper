"""Laptop reference resolver: normalize brand/model/display_size and find/create the
matching row in `laptop_reference`.

Tolerances (intentionally conservative — only safe normalizations, no fuzzy matching):

* **brand** — case-insensitive + trim. "Apple" == "apple" == " APPLE ".
* **display_size** — keep digits and a single dot. Strip inch marks / "inch" / "collas".
  We do NOT strip trailing ".0" so the key matches the existing `laptop_reference`
  rows from the original migration.
* **model** — case-insensitive + trim + collapse whitespace, PLUS:
  - strip parenthetical content: "Macbook Pro (2019)" -> "macbook pro"
  - strip leading/trailing Latvian ad words: "klēpjdators", "portatīvais", "dators".
    English words like "Gaming", "Notebook", "Laptop" are NOT stripped because
    they appear inside real product names (TUF Gaming A15, Envy Notebook,
    Surface Laptop) — false merges there are worse than the extra duplicates
    we accept.
  - DO NOT fuzzy-match typos (e.g. "Macbook" vs "Macbok" stays split — admin merges later)
  - DO NOT strip model-name tokens like "M2", "Pro", "Air", "i5", "X1", "840", "14"
  - DO NOT strip trailing numbers that happen to equal the display size — many
    real model names contain the size ("XPS 13", "Cyborg 15", "Vivobook Go 15",
    "Macbook Pro 14 M2"). Stripping them is unsafe; admin merges via the VALID mark
    handle the few "Macbook air 13" duplicates.

These rules are enough to collapse the most common case-variant and whitespace
noise without false-merging distinct models. Anything that needs human judgment
(typos, Apple A-numbers vs retail names, "Proo" vs "Pro") stays split and goes
through the admin VALID + merge workflow.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Pure normalization helpers (no DB, easy to unit-test)
# ---------------------------------------------------------------------------

def normalize_brand(brand: Optional[str]) -> str:
    if not brand:
        return ""
    return re.sub(r"\s+", " ", brand).strip().lower()


# Match the display-size forms we see in scraped data: "13", "13.3", "13\"", "13 inch", "13 collas"
_DISPLAY_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)")
_TRAILING_SIZE_TOKENS_RE = re.compile(
    # Optional " (something)" or trailing inch mark/word, then capture a number.
    r"[\s\-]*[\(" r"\)]*[\s\-]*"
    r'(?:"|″|”|“|`|inch|collas|collu|")?'
    r"\s*$",
    re.IGNORECASE,
)
_PARENS_RE = re.compile(r"\([^)]*\)")
_AD_WORDS = ['klēpjdators', 'portatīvais', 'dators']
_LEADING_AD_RE = re.compile(r"^\s*(?:" + "|".join(_AD_WORDS) + r")\s+", re.IGNORECASE)
_TRAILING_AD_RE = re.compile(r"\s+(?:" + "|".join(_AD_WORDS) + r")\s*$", re.IGNORECASE)


def _strip_ad_words_iter(s: str) -> str:
    """Repeatedly strip leading/trailing ad-words (handles "Portatīvais dators X")."""
    for _ in range(5):  # bounded to avoid pathological input
        new_s = _LEADING_AD_RE.sub("", s)
        new_s = _TRAILING_AD_RE.sub("", new_s)
        if new_s == s:
            return s
        s = new_s
    return s


def normalize_display_size(display_size: Optional[str]) -> str:
    """Return the size as a string of digits and a single optional dot.
    Drops inch marks, "inch", "collas".

    Note: we do NOT strip trailing ".0" so the key matches the existing
    `laptop_reference.normalized_key` rows populated by the original migration
    (`migrations/create_laptop_reference_table.sql`).

    >>> normalize_display_size('13"')
    '13'
    >>> normalize_display_size('13.0')
    '13.0'
    >>> normalize_display_size('15.6 inch')
    '15.6'
    >>> normalize_display_size(None)
    ''
    """
    if not display_size:
        return ""
    s = str(display_size).strip()
    m = _DISPLAY_SIZE_RE.search(s)
    if not m:
        return ""
    return m.group(1)


def _strip_trailing_size(model: str, display_size_norm: str) -> str:
    """UNUSED — kept for reference.

    We do NOT strip a trailing number from the model even when it matches the
    display size. Many real model names contain the size ("XPS 13", "Cyborg 15",
    "Vivobook Go 15", "Macbook Pro 14 M2") so a strip-by-display-size rule
    produced 43 false merges in the test dataset (Dell XPS 13 / XPS 13 (7390),
    MSI Sword 17, Asus Vivobook Go 15, etc.). Admin merges via the VALID mark
    handle the few true duplicates like "Macbook air 13" vs "Macbook Air".
    """
    return model


def normalize_model(model: Optional[str], display_size: Optional[str] = None) -> str:
    """Apply all model tolerances. See module docstring for the rules.

    `display_size` is accepted for API symmetry but currently unused.
    """
    if not model:
        return ""
    s = str(model)
    s = _PARENS_RE.sub("", s)
    s = _strip_ad_words_iter(s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    # After stripping, the model may end in punctuation; trim again.
    s = re.sub(r"[\s,;:\-]+$", "", s).strip()
    return s


def normalized_key(brand: Optional[str], model: Optional[str], display_size: Optional[str]) -> str:
    """Return the canonical key for the (brand, model, display_size) tuple.

    Returns empty string if brand or model is missing — callers should treat that
    as "no reference" and leave laptop_reference_id NULL.
    """
    b = normalize_brand(brand)
    m = normalize_model(model, display_size)
    if not b or not m:
        return ""
    d = normalize_display_size(display_size)
    return f"{b}|{m}|{d}"


# ---------------------------------------------------------------------------
# Resolution: look up the FK, create on miss
# ---------------------------------------------------------------------------

# Resolution auto-extract: "1920x1080", "1920×1080", "2560 x 1600"
_RESOLUTION_RE = re.compile(r"(\d{3,4})\s*[x×]\s*(\d{3,4})")

# Refresh rate auto-extract: "144Hz", "144 Hz", "144Hz", "120Hz", "60Hz".
# Accepts the common case-insensitive 'hz' suffix. We also allow a leading
# word boundary so we don't match e.g. "2440mAh" or similar. The numeric
# group is constrained to 30-1000 to filter out phone-style "Hz" of audio
# or any 3+ digit gibberish.
_REFRESH_RATE_RE = re.compile(r"(?<![A-Za-z0-9])(\d{2,3})\s*[Hh][Zz]\b")

# Model number / SKU auto-extract from the listing description. We try a
# small set of patterns and pick the longest match (longer SKUs are
# usually more specific). Common CPU model numbers (e.g. "1135G7") are
# filtered out so they don't pollute the result.
_SKU_PATTERNS = [
    re.compile(r"\b([A-Z]{1,2}\d{3,5})(?:[-/](\d{1,3}[A-Z]?))?\b", re.IGNORECASE),  # A515, A515-58P
    re.compile(r"\b(\d{4,5}[A-Z]{1,3})\b", re.IGNORECASE),                          # 5520U, 1135G7
    re.compile(r"\b([A-Z]\d{1,4}[A-Z]?)\b", re.IGNORECASE),                          # G7, T14, X13, A1466
]
_SKU_FALSE_POSITIVES = {
    "I3", "I5", "I7", "I9", "M1", "M2", "M3", "M4", "M5",
    "X1", "X2", "X3", "X4", "X5",
    "OK", "IT", "ID", "TV", "PC", "GB", "TB", "USD", "EUR",
    "HD", "SD", "USB", "RAM", "SSD", "HDD", "HDMI", "WIFI",
    "W11", "W10", "WIN11", "WIN10",
    "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025",
    "13", "14", "15", "16", "17", "12",
}
# CPU model numbers: 1-7 + 3-4 digits + 1-2 letter suffix (e.g. "1135G7",
# "1255U", "5500U", "4600H"). These show up in the description but aren't
# the laptop SKU.
_SKU_CPU_MODEL_RE = re.compile(r"^[1-7]\d{3,4}[A-Z]{1,2}$")


def _extract_model_number_from_description(description: Optional[str]) -> Optional[str]:
    """Best-effort SKU / model-number extraction from the description.

    Returns the first plausible SKU or None. Conservative: filters out common
    false positives and CPU model numbers. Admin can refine via the edit
    panel.
    """
    if not description:
        return None
    candidates: list[str] = []
    for pat in _SKU_PATTERNS:
        for m in pat.finditer(description):
            groups = m.groups()
            sku = groups[0]
            if len(groups) > 1 and groups[1]:
                sku = f"{groups[0]}-{groups[1]}"
            sku = sku.upper()
            if sku in _SKU_FALSE_POSITIVES or _SKU_CPU_MODEL_RE.match(sku):
                continue
            candidates.append(sku)
    if not candidates:
        return None
    # Prefer the longest match — more specific SKUs (A515-58P) beat shorter
    # substrings (A515, A51) that would have been captured too.
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _extract_resolution_from_description(description: Optional[str]) -> Optional[str]:
    """Return the first WxH resolution in the description, in canonical "WxH" form."""
    if not description:
        return None
    m = _RESOLUTION_RE.search(description)
    if not m:
        return None
    return f"{m.group(1)}x{m.group(2)}"


def _extract_refresh_rate_hz(description: Optional[str]) -> Optional[int]:
    """Return the first plausible refresh rate (Hz) from the description.

    Matches patterns like "144Hz", "144 Hz", "120Hz", "60Hz" — common in
    laptop marketing blurbs ("...144Hz refresh rate..."). Filters out
    unlikely values (audio Hz, 4-digit numbers from resolution strings).

    Most laptop listings don't mention a refresh rate at all. The
    industry-standard default for unspecified panels is 60 Hz, so we
    return that here. The resolver also returns 60 when the input is
    missing entirely.
    """
    if not description:
        return 60
    m = _REFRESH_RATE_RE.search(description)
    if not m:
        return 60
    n = int(m.group(1))
    if not 30 <= n <= 1000:
        return 60
    return n


class LaptopReferenceResolver:
    """Look up `laptop_reference.id` for a (brand, model, display_size) tuple,
    creating the row if it does not exist.

    Uses an UPSERT on the UNIQUE `normalized_key` so concurrent calls are safe.
    """

    def __init__(self, session: Session):
        self.session = session

    def resolve(
        self,
        brand: Optional[str],
        model: Optional[str],
        display_size: Optional[str],
        description: Optional[str] = None,
    ) -> Tuple[Optional[int], str]:
        """Return (laptop_reference_id, normalized_key). If the key is empty (no
        brand/model), returns (None, ''). New rows are auto-created on miss.
        """
        key = normalized_key(brand, model, display_size)
        if not key:
            return None, ""

        row = self.session.execute(
            text("SELECT id FROM laptop_reference WHERE normalized_key = :k"),
            {"k": key},
        ).fetchone()
        if row:
            return row[0], key

        resolution = _extract_resolution_from_description(description)
        refresh_rate_hz = _extract_refresh_rate_hz(description)
        # Best-effort model number extraction from the description. Admin can
        # refine anything the heuristics get wrong via the edit panel.
        model_number = _extract_model_number_from_description(description)
        # Use the human-friendly brand/model from the input (not the normalized form)
        # so the staff sees what the listing actually said.
        db_brand = (brand or "").strip() or "(unknown)"
        db_model = (model or "").strip() or "(unknown)"
        db_size = (display_size or "").strip() or None

        inserted = self.session.execute(
            text("""
                INSERT INTO laptop_reference
                    (brand, model, model_number, display_size, normalized_key, resolution, refresh_rate_hz)
                VALUES (:brand, :model, :model_number, :display_size, :key, :resolution, :refresh_rate_hz)
                ON CONFLICT (normalized_key) DO UPDATE
                    SET normalized_key = EXCLUDED.normalized_key
                RETURNING id
            """),
            {
                "brand": db_brand,
                "model": db_model,
                "model_number": model_number,
                "display_size": db_size,
                "key": key,
                "resolution": resolution,
                "refresh_rate_hz": refresh_rate_hz,
            },
        ).fetchone()
        return inserted[0], key
