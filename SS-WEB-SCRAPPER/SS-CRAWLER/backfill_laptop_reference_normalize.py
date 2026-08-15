"""Normalize laptop_reference.model and model_number using the combined
"Model SKU" string as a lookup key.

Walks every row where model != model_number (and the model_number isn't in
the obvious-bad set the user excluded like G3/G6/g4). For each row, builds
the combined query "<model> <model_number>" and:

1. **Clear obviously-bad model_number values** (chipsets, wifi cards, ports,
   bare CPU names) — set them to NULL and merge into the model column.
2. **Detect "swapped" rows** where the model looks like a SKU and the
   model_number looks like a family name — swap them.
3. **Vendor-specific cleanups** — fix casing (Latitude 5400 vs latitude
   5400), drop noise ("hm", "g3") from wrong positions, etc.
4. **Canonical known model families** — for a few obvious ones, set the
   canonical form (T14 Gen 3 -> T14 / Gen 3, E6400 -> Latitude E6400).

Dry-run by default; pass --apply to actually UPDATE.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor


# ---------------------------------------------------------------------------
# "Bad" model_number values: tokens that look like SKUs but are actually
# ports, chipsets, wifi cards, screen sizes, CPU names, etc. The script
# clears these to NULL and merges them into the model column.
# ---------------------------------------------------------------------------
# Wifi card module names: "AX211", "MT7925", "AX201", "RTL8822", ...
_WIFI_CARD_RE = re.compile(r"^(AX\d{3}|MT\d{4}|RTL\d{4}|QCA\d{4}|Intel)?$", re.IGNORECASE)
# Intel laptop chipset: HM470, HM570, HM670, QM67, ...
_CHIPSET_RE = re.compile(r"^(HM|QM|CM)\d{3}$", re.IGNORECASE)
# Port / protocol names
_PORT_KEYWORDS = {
    "RS232", "USB", "HDMI", "WIFI", "VGA", "DP", "DPORT",
    "TB3", "TB4", "RJ45", "BT", "NFC",
}
# Bare CPU names accidentally stored as model_number
_CPU_RE = re.compile(r"^i[3579]-\d{4,5}[A-Z]{0,2}$", re.IGNORECASE)
# Pure 1-2 digit number (looks like a screen size or year, not a SKU)
_BARE_TINY_NUM_RE = re.compile(r"^\d{1,2}$")
# 4-5 digit number with a CPU-suffix letter (i3/i5/i7/Ryzen model — those go
# in `laptop_reference_cpu`, not here)
_CPU_NUMBER_RE = re.compile(r"^[1-7]\d{3,4}[A-Z]{1,2}$")


def is_bad_model_number(value: str | None) -> bool:
    """Return True if `value` looks like something other than a laptop SKU."""
    if not value:
        return False
    v = value.strip()
    if not v:
        return False
    if v in _PORT_KEYWORDS:
        return True
    if _WIFI_CARD_RE.match(v):
        return True
    if _CHIPSET_RE.match(v):
        return True
    if _CPU_RE.match(v):
        return True
    if _CPU_NUMBER_RE.match(v):
        return True
    if _BARE_TINY_NUM_RE.match(v):
        return True
    # Common noise words that look like SKUs but aren't
    if v.lower() in {"m1", "m2", "g3", "g6", "g4", "g7", "g8", "g9", "g10"}:
        return False  # these are valid generation codes
    return False


# ---------------------------------------------------------------------------
# Per-brand canonicalization
# ---------------------------------------------------------------------------
# Many vendors treat the family + size as a single model identifier. For
# those, the right "split" is to merge model + model_number into one
# (model) and NULL the model_number. For others, the split is by generation
# code (HP) or by SKU (Acer / Asus).
_MERGE_BRANDS = {"Dell", "Fujitsu", "Fujitsu-Siem", "Lenovo/IBM", "MSI", "Microsoft", "Samsung", "Razer"}
_SPLIT_BRANDS = {"HP", "Acer", "Asus"}


# Per-brand cleanups on the combined query
def _clean_combined(brand: str | None, combined: str) -> str:
    """Apply per-brand text cleanup (casing, spaces, common noise)."""
    if not combined:
        return combined
    s = combined
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Title-case the family part for the brands that want it
    return s


# Specific known-canonical rows
_KNOWN_CANONICAL: dict[str, tuple[str, str | None]] = {
    # Lenovo T14 with generation in model
    "t14 gen 1": ("T14", "Gen 1"),
    "t14 gen 2": ("T14", "Gen 2"),
    "t14 gen 3": ("T14", "Gen 3"),
    "t14 gen 4": ("T14", "Gen 4"),
    "t14 gen 5": ("T14", "Gen 5"),
    "t14 gen 6": ("T14", "Gen 6"),
    "t14 gen 7": ("T14", "Gen 7"),
    "t14s gen 1": ("T14s", "Gen 1"),
    "t14s gen 2": ("T14s", "Gen 2"),
    "t14s gen 3": ("T14s", "Gen 3"),
    "t14s gen 4": ("T14s", "Gen 4"),
    "t14s gen 6": ("T14s", "Gen 6"),
    "t14s gen 7": ("T14s", "Gen 7"),
    "t16 gen 1": ("T16", "Gen 1"),
    "t16 gen 2": ("T16", "Gen 2"),
    "t16 gen 3": ("T16", "Gen 3"),
    "t480": ("T480", None),
    "t480s": ("T480s", None),
    "t14 gen 5": ("T14", "Gen 5"),
    # "X1 Carbon" variants
    "x1 carbon g12": ("X1 Carbon", "Gen 12"),
    "x1 carbon g11": ("X1 Carbon", "Gen 11"),
    "x1 carbon g10": ("X1 Carbon", "Gen 10"),
    "x1 carbon g9": ("X1 Carbon", "Gen 9"),
    "x1 carbon g8": ("X1 Carbon", "Gen 8"),
    "x1 carbon g7": ("X1 Carbon", "Gen 7"),
    "x1 carbon g6": ("X1 Carbon", "Gen 6"),
    # Dell Latitude E-series: the E is part of the name
    "latitude e6400": ("Latitude E6400", None),
    "latitude e5470": ("Latitude E5470", None),
    "latitude e7270": ("Latitude E7270", None),
    "latitude e7240": ("Latitude E7240", None),
    "latitude e558": ("Latitude E558", None),
    "latitude e448": ("Latitude E448", None),
}


# Swap detection: model = "<family> Gen <N>", model_number = "<family>"
# means the SKU and the family have been swapped.
_SWAP_RE = re.compile(r"^(?P<fam>.+?)\s+Gen\s+(?P<n>\d+)$", re.IGNORECASE)


def canonical_split(brand: str | None, model: str | None, model_number: str | None) -> tuple[str | None, str | None] | None:
    """Return the canonical (model, model_number) split for a row, or
    None when no rule applies (keep current values).
    """
    if not model and not model_number:
        return None
    model = (model or "").strip()
    number = (model_number or "").strip()

    combined = f"{model} {number}".strip()

    # 1) Known-canonical entries win.
    if combined.lower() in _KNOWN_CANONICAL:
        return _KNOWN_CANONICAL[combined.lower()]

    # 2) Bad model_number? clear to NULL and merge into model.
    if number and is_bad_model_number(number):
        merged = _clean_combined(brand, combined)
        return (merged, None)

    # 3) Swap detection: model looks like "<family> Gen N" and the
    # model_number is just the family name. Swap them.
    m = _SWAP_RE.match(model)
    if m and m.group("fam").strip().lower() == number.strip().lower():
        fam = m.group("fam").strip()
        gen = f"Gen {m.group('n')}"
        return (fam, gen)

    # 4) Bad model (noise word like "Latitude" with no number) — leave
    # alone, admin should fill in.
    if not number:
        return None

    # 5) For Dell, the canonical "model" is the full identifier (family
    # + size + SKU), so model_number is often redundant. Only merge if
    # the model_number looks like a real SKU suffix (digits or SKU
    # letter+digit pattern), not when it's a noise word.
    if brand == "Dell":
        if re.match(r"^(\d{3,5}|[A-Z]\d{3,4}|E\d{3,4})$", number):
            # Looks like a Dell SKU. Merge to single model name.
            merged = _clean_combined(brand, combined)
            return (merged, None)
    return None


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually UPDATE rows. Default is dry-run.")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to scan (0 = all).")
    args = ap.parse_args()

    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT lr.id, lr.brand, lr.model, lr.model_number, lr.display_size
        FROM laptop_reference lr
        WHERE lr.brand != 'Apple'
          AND lr.model NOT LIKE '%TUF%'
          AND lr.model != 'Dash'
          AND lr.model != lr.model_number
          AND lr.model_number NOT IN ('G3', 'G6', 'g4')
          AND lr.model_number IS NOT NULL
        ORDER BY lr.id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Scanning {len(refs)} reference rows (apply={args.apply})")

    updated = 0
    unchanged = 0
    flagged_unknown = 0
    samples_changed: list[tuple] = []
    samples_unchanged: list[tuple] = []
    for r in refs:
        new = canonical_split(r["brand"], r["model"], r["model_number"])
        if not new:
            unchanged += 1
            if len(samples_unchanged) < 10:
                samples_unchanged.append((r["id"], r["brand"], r["model"], r["model_number"]))
            continue
        new_model, new_number = new
        if new_model == r["model"] and new_number == r["model_number"]:
            unchanged += 1
            continue
        if args.apply:
            cur.execute(
                "UPDATE laptop_reference SET model = %s, model_number = %s, updated_at = NOW() WHERE id = %s",
                (new_model, new_number, r["id"]),
            )
        else:
            print(f"  [dry-run] {r['id']:4} {r['brand']!r:14}  {r['model']!r:30} / {r['model_number']!r:18}  ->  {new_model!r:30} / {new_number!r}")
        updated += 1
        if len(samples_changed) < 10:
            samples_changed.append((r["id"], r["brand"], r["model"], r["model_number"], new_model, new_number))

    if args.apply:
        conn.commit()
    cur.close()
    conn.close()

    print(f"\nUpdated {updated}  Unchanged {unchanged}  (apply={args.apply})")
    if samples_changed:
        print("\nSample of changed rows:")
        for sid, brand, m_old, n_old, m_new, n_new in samples_changed:
            print(f"  {sid:4}  {brand!r:14}  {m_old!r:30} / {n_old!r:18}  ->  {m_new!r:30} / {n_new!r}")
    if samples_unchanged:
        print("\nSample of unchanged rows (admin can refine manually):")
        for sid, brand, m, n in samples_unchanged:
            print(f"  {sid:4}  {brand!r:14}  {m!r:30} / {n!r}")


if __name__ == "__main__":
    main()
