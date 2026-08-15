"""CPU reference resolver: normalize a raw CPU string (e.g. "Intel Core i7-11400H")
into a canonical (brand, model) pair and find/create the matching row in
`laptop_reference_cpu`.

Canonical model format (matches Intel/AMD/Apple/Qualcomm conventions):

* Intel:    "i7-11400H", "i5-12500U", "i9-13900HX", "Celeron N4020", "Pentium Gold 7505"
* AMD:      "Ryzen 7 5800H", "Ryzen 5 5500U"
* Apple:    "M2", "M2 Pro", "M2 Max", "M3"
* Qualcomm: "Snapdragon X Elite", "Snapdragon 8cx Gen 3"

Tolerances:

1. **Drop vendor/brand prefixes** (case-insensitive): "Intel", "Intel(R)", "Intel(R) Core(TM)",
   "Intel Core", "AMD", "Amd", "Apple", "Qualcomm"
2. **Drop registered/trademark marks**: "(R)", "(TM)", "(®)", "(™)"
3. **Drop suffix clutter**: "@ 2.60GHz", " Processor", " CPU", " Series"
4. **Collapse whitespace** and trim
5. **Normalize Intel case**: lowercase class letter (i7, i5, i3, i9), then digits, then
   uppercase suffix letter (H, U, G, etc.) — e.g. "I5-1135g7" -> "i5-1135G7"
6. **Normalize AMD case**: capitalize vendor prefix "Ryzen" — "ryzen 7 5800h" -> "Ryzen 7 5800H"
7. **Normalize Apple case**: capitalize M — "m2" -> "M2", "apple m2 pro" -> "M2 Pro"
8. **Normalize Qualcomm case**: capitalize "Snapdragon" — "snapdragon x elite" -> "Snapdragon X Elite"
9. **Map bare class names** without a model number:
   * "Intel Core i5" (no model) -> "i5"
   * "AMD Ryzen 5" -> "Ryzen 5"
   * "Apple M2" -> "M2"
10. **Map common abbreviations**: "I5" -> "i5", "Ryzen5" -> "Ryzen 5"
11. **Drop trailing size numbers that match the laptop display** (e.g. "i5-1135G7 14" -> "i5-1135G7")

Empty / nonsense inputs (e.g. "Intel", "Processor", "CPU") return (None, "", "")
so callers can leave the FK NULL.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Pure normalization helpers
# ---------------------------------------------------------------------------

# Replace (R)/(TM)/(®)/(™) marks with a single space — with or without surrounding whitespace
_MARKS_RE = re.compile(
    r"\s*[\(\[]\s*[rR]\s*[\)\]]"     # (R) / (r)
    r"|\s*[\(\[]\s*(?:TM|tm|®|™)\s*[\)\]]",  # (TM) / (®) / (™)
    re.IGNORECASE,
)
_MARKS_REPLACEMENT = " "

# Drop clock speeds and trailing unit noise
_CLOCK_RE = re.compile(r"\s*@\s*[\d.]+\s*ghz\s*", re.IGNORECASE)
_SUFFIX_NOISE_RE = re.compile(
    r"\s+(?:processor|series|cpu|chip)$", re.IGNORECASE
)

# Brand prefixes to strip (in order of priority — most-specific first)
_INTEL_PREFIXES = [
    r"intel\(r\)\s+core\(tm\)\s*",
    r"intel\(r\)\s*core\(tm\)\s*",
    r"intel\s+core\(tm\)\s*",
    r"intel\s+core\s*",
    r"intel\(r\)\s*",
    r"intel\s*",
    r"inter\s*",  # common ss.com typo for "Intel"
    r"core\s+",  # bare "Core i5" with no Intel prefix
]
_AMD_PREFIXES = [
    # Note: do NOT strip "Ryzen" — it carries vendor signal.
    # Just strip the "AMD" / "Amd" prefix.
    r"amd\s*",
]
_APPLE_PREFIXES = [
    r"apple\s+silicon\s*",
    r"apple\s+",
]
_QUALCOMM_PREFIXES = [
    r"qualcomm\s+",
]

# Trailing size number (matches "i5-1135G7 14" -> "i5-1135G7").
# CRITICAL: only 1-2 digit numbers are screen sizes (13, 14, 15.6, 17).
# 3+ digit numbers are model numbers (7505, 5800) and must NOT be stripped.
_TRAILING_SIZE_RE = re.compile(r"\s+\d{1,2}(?:\.\d+)?[\"″]?\s*$")

# Model-number patterns to detect a "real" Intel SKU vs a bare class.
# Intel suffix forms: single letter (H, U), letter+digit (G7, G4), two letters (HK, HX),
# letter+digit+letter (G7E, G1E), or two letters+digit (rare). The suffix is
# OPTIONAL — desktop parts like i5-7200, i5-10400, i5-13400 have no letter.
# The pattern ([a-z][0-9a-z]{0,2})? matches the suffix if present.
_INTEL_SKU_RE = re.compile(r"^i[3579]-\d{4,6}([a-z][0-9a-z]{0,2})?$", re.IGNORECASE)
_INTEL_BARE_CLASS_RE = re.compile(r"^i[3579]$", re.IGNORECASE)
_INTEL_CLASS_RE = re.compile(r"^i([3579])$", re.IGNORECASE)
_INTEL_PENTIUM_CELERON_RE = re.compile(r"^(pentium|celeron|atom|xeon)(\s+.+)?$", re.IGNORECASE)

# AMD SKU patterns — allow 1-2 letter suffixes (H, U, HS, HX) for real-world data
_AMD_SKU_RE = re.compile(r"^ryzen\s+[3579](\s+pro)?\s+\d{4,5}[a-z]{0,2}$", re.IGNORECASE)
_AMD_BARE_CLASS_RE = re.compile(r"^ryzen\s+[3579]$", re.IGNORECASE)
_AMD_CLASS_RE = re.compile(r"^ryzen\s+([3579])$", re.IGNORECASE)

# Apple
_APPLE_SKU_RE = re.compile(r"^m[1-4](\s+(pro|max|ultra))?$", re.IGNORECASE)
_APPLE_BARE_RE = re.compile(r"^m[1-4]$", re.IGNORECASE)

# Qualcomm / Snapdragon
_SNAPDRAGON_RE = re.compile(r"^snapdragon(\s+.+)?$", re.IGNORECASE)


def _strip_prefixes(s: str) -> str:
    """Strip brand prefixes (Intel/AMD/Apple/Qualcomm) from the start of the string."""
    for prefix in _INTEL_PREFIXES + _AMD_PREFIXES + _APPLE_PREFIXES + _QUALCOMM_PREFIXES:
        s = re.sub(r"^" + prefix, "", s, flags=re.IGNORECASE)
    return s


def _strip_marks_and_noise(s: str) -> str:
    s = _MARKS_RE.sub(_MARKS_REPLACEMENT, s)
    s = _CLOCK_RE.sub(" ", s)
    s = _SUFFIX_NOISE_RE.sub("", s)
    return s


def _canonicalize_intel(model: str) -> str:
    """Convert "i5-1135g7" -> "i5-1135G7", "I5" -> "i5", "Pentium Gold 7505" -> "Pentium Gold 7505"."""
    # Intel SKUs: i7-11400H -> normalize the suffix (optional: desktop parts have no suffix).
    m = re.match(r"^i([3579])-(\d{4,6})([a-z][0-9a-z]{0,2})?$", model, re.IGNORECASE)
    if m:
        cls = m.group(1).lower()
        num = m.group(2)
        suffix = m.group(3) or ""
        # Suffix: uppercase all letters, digits stay as-is.
        # "g7" -> "G7", "hx" -> "HX", "g7e" -> "G7E"; missing suffix stays empty.
        if suffix:
            suffix = suffix.upper()
        return f"i{cls}-{num}{suffix}"
    # Bare Intel class: "i5" -> "i5"
    m = re.match(r"^i([3579])$", model, re.IGNORECASE)
    if m:
        return f"i{m.group(1).lower()}"
    # Pentium/Celeron/Atom/Xeon: keep first letter capital, rest lowercase for the class word
    m = re.match(r"^(pentium|celeron|atom|xeon)(\s+.+)?$", model, re.IGNORECASE)
    if m:
        cls = m.group(1).capitalize()
        rest = (m.group(2) or "").strip()
        if rest:
            return f"{cls} {rest}"
        return cls
    return model


def _canonicalize_amd(model: str) -> str:
    """Convert "ryzen 7 5800h" -> "Ryzen 7 5800H", "amd ryzen 5" -> "Ryzen 5"."""
    # AMD SKUs: ryzen 7 5800H, ryzen 5 pro 4650U, etc.
    m = re.match(r"^ryzen\s+([3579])(\s+pro)?\s+(\d{4,5})([a-z]?)$", model, re.IGNORECASE)
    if m:
        cls = m.group(1)
        pro = " Pro" if m.group(2) else ""
        num = m.group(3)
        suffix = m.group(4).upper() if m.group(4) else ""
        return f"Ryzen {cls}{pro} {num}{suffix}"
    # Bare class: "ryzen 5" -> "Ryzen 5"
    m = re.match(r"^ryzen\s+([3579])$", model, re.IGNORECASE)
    if m:
        return f"Ryzen {m.group(1)}"
    return model


def _canonicalize_apple(model: str) -> str:
    """Convert "apple m2" -> "M2", "m2 pro" -> "M2 Pro"."""
    m = re.match(r"^m([1-4])(\s+(pro|max|ultra))?$", model, re.IGNORECASE)
    if m:
        return f"M{m.group(1)}{(m.group(2) or '').title()}"
    return model


def _canonicalize_snapdragon(model: str) -> str:
    """Convert "snapdragon x elite" -> "Snapdragon X Elite", "qualcomm snapdragon 8cx gen 3" -> "Snapdragon 8cx Gen 3"."""
    m = re.match(r"^snapdragon(\s+(x\s+elite|8cx|7c|\d+\w*))?(\s+gen\s+\d+)?$", model, re.IGNORECASE)
    if m:
        rest = m.group(2) or ""
        gen = (m.group(3) or "").strip()
        rest_clean = " ".join(w.capitalize() if not w.isdigit() else w for w in rest.split())
        if gen:
            gen_clean = " ".join(w.capitalize() for w in gen.split())
            return f"Snapdragon {rest_clean} {gen_clean}".strip()
        return f"Snapdragon {rest_clean}".strip()
    return model


def _drop_trailing_size(model: str) -> str:
    """Drop a trailing screen-size number (e.g. "i5-1135G7 14" -> "i5-1135G7").

    Only applies to full SKUs (models containing a 4+ digit number like "1135",
    "5800", "7505"). For bare class names like "ryzen 5" or "i5" we keep the
    class number intact — we can't tell a screen size from a class number.
    """
    if not re.search(r"\d{4,}", model):
        return model
    return _TRAILING_SIZE_RE.sub("", model).strip()


def _classify_vendor(model: str) -> str:
    """Classify the vendor based on the model name."""
    if not model:
        return ""
    m = model.lower()
    if m.startswith("i") and re.match(r"^i[3579](-\d+|$)", m):
        return "Intel"
    if m.startswith("i") and _INTEL_PENTIUM_CELERON_RE.match(m):
        return "Intel"
    # Pentium / Celeron / Atom / Xeon are also Intel — no "i" prefix needed
    if _INTEL_PENTIUM_CELERON_RE.match(m):
        return "Intel"
    if m.startswith("ryzen"):
        return "AMD"
    if re.match(r"^m[1-4](\s|$)", m):
        return "Apple"
    if m.startswith("snapdragon"):
        return "Qualcomm"
    return ""


def normalize_cpu_name(raw: Optional[str]) -> Tuple[Optional[str], str, str]:
    """Return (brand, model, normalized_key) for a raw CPU string.

    - brand: "Intel" / "AMD" / "Apple" / "Qualcomm" / "" (empty if not classifiable)
    - model: canonical model string ("i7-11400H", "Ryzen 7 5800H", "M2", ...)
    - normalized_key: `lower(brand)|lower(model)` or "" if not classifiable

    Empty / non-CPU inputs ("", "Intel", "Processor") return (None, "", "").
    """
    if not raw:
        return None, "", ""
    s = str(raw).strip()
    if not s:
        return None, "", ""

    # 1) Drop the (R)/(TM)/(®)/(™) marks, the @ N.NNGHz clock, the trailing
    #    "Processor"/"Series"/"CPU" noise.
    s = _strip_marks_and_noise(s)

    # 2) Collapse internal whitespace.
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None, "", ""

    # 3) Strip brand prefixes.
    s = _strip_prefixes(s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None, "", ""
    # Reject inputs that have no letters/digits (e.g. "@", "???")
    if not re.search(r"[a-z0-9]", s, re.IGNORECASE):
        return None, "", ""
    # Reject bare noise words (e.g. "Processor", "CPU", "Series")
    if s.lower() in {"processor", "series", "cpu", "chip"}:
        return None, "", ""

    # 4) Drop trailing size number.
    s = _drop_trailing_size(s)
    if not s:
        return None, "", ""

    # 5) Decide vendor from the model first (so we can canonicalize correctly).
    vendor = _classify_vendor(s)

    # 6) Canonicalize by vendor.
    if vendor == "Intel":
        model = _canonicalize_intel(s)
    elif vendor == "AMD":
        model = _canonicalize_amd(s)
    elif vendor == "Apple":
        model = _canonicalize_apple(s)
    elif vendor == "Qualcomm":
        model = _canonicalize_snapdragon(s)
    else:
        # Unknown vendor — try to canonicalize as Intel (most common); else
        # leave the model with title-case on the first word.
        model = _canonicalize_intel(s) if _INTEL_SKU_RE.match(s) or _INTEL_BARE_CLASS_RE.match(s) else s
        if not model:
            return None, "", ""

    if not model:
        return None, "", ""

    # 7) Build the normalized key.
    key = f"{vendor.lower()}|{model.lower()}" if vendor else model.lower()
    return vendor or None, model, key


# ---------------------------------------------------------------------------
# Resolution: look up the FK, create on miss
# ---------------------------------------------------------------------------

# Mirrors _RESOLUTION_RE in the laptop_reference_resolver
_RESOLUTION_RE = re.compile(r"(\d{3,4})\s*[x×]\s*(\d{3,4})")


def _extract_resolution_from_description(description: Optional[str]) -> Optional[str]:
    if not description:
        return None
    m = _RESOLUTION_RE.search(description)
    if not m:
        return None
    return f"{m.group(1)}x{m.group(2)}"


class CPUReferenceResolver:
    """Look up `laptop_reference_cpu.id` for a raw CPU string, creating the row on miss.

    Uses an UPSERT on the UNIQUE `normalized_key` so concurrent calls are safe.
    """

    def __init__(self, session: Session):
        self.session = session

    def resolve(
        self,
        cpu_raw: Optional[str],
        description: Optional[str] = None,
    ) -> Tuple[Optional[int], str, str]:
        """Return (cpu_reference_id, normalized_key, normalized_model). If the CPU is
        not classifiable (e.g. "Intel" with no model), returns (None, '', '').
        """
        brand, model, key = normalize_cpu_name(cpu_raw)
        if not key or not model:
            return None, "", ""

        row = self.session.execute(
            text("SELECT id FROM laptop_reference_cpu WHERE normalized_key = :k"),
            {"k": key},
        ).fetchone()
        if row:
            return row[0], key, model

        # Optional context columns (best-effort, do not block creation)
        # We don't have a generation/tier column on laptop_reference_cpu today;
        # if added later, compute here.
        inserted = self.session.execute(
            text("""
                INSERT INTO laptop_reference_cpu
                    (brand, model, normalized_key)
                VALUES (:brand, :model, :key)
                ON CONFLICT (normalized_key) DO UPDATE
                    SET normalized_key = EXCLUDED.normalized_key
                RETURNING id
            """),
            {"brand": brand, "model": model, "key": key},
        ).fetchone()
        return inserted[0], key, model
