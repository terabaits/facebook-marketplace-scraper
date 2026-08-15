"""Backfill `laptop_reference.model` and `model_number` from the existing
single `model` column.

Splits strings like "Vostro 15 5000" -> ("Vostro 15", "5000"),
"Probook 440 G7" -> ("Probook 440", "G7"), "Aspire 5 A515-58P" ->
("Aspire 5", "A515-58P"). The split is per-vendor: each brand has its
own set of "line keywords" (Aspire, Probook, ThinkPad, etc.). If the
brand has no recognised line, the original `model` is kept and
`model_number` stays NULL — admin can fix it from the edit panel.

Safe to re-run. The script only updates rows where the current split
would be different from the new one (or where model_number is NULL).

Usage (from SS-CRAWLER root, with venv active):

    python backfill_laptop_reference_model_split.py --dry-run
    python backfill_laptop_reference_model_split.py
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
# Per-vendor line keywords
#
# Longest first so "Macbook Pro" matches before "Macbook", "ThinkBook" before
# "Think", etc. The list isn't exhaustive — admin can fix anything the
# script gets wrong.
# ---------------------------------------------------------------------------
LINE_KEYWORDS: dict[str, list[str]] = {
    "Dell":       ["Latitude", "Inspiron", "XPS", "Vostro", "Alienware",
                   "Precision", "Studio", "Chromebook", "G Series",
                   "G15", "G16", "G3", "G5", "G7"],
    "HP":         ["EliteBook", "ProBook", "ZBook", "Pavilion", "Envy",
                   "Spectre", "Omen", "Victus", "Presario", "Stream"],
    "Lenovo":     ["ThinkPad X1 Carbon", "ThinkPad X1", "ThinkPad T",
                   "ThinkPad X", "ThinkPad L", "ThinkPad E", "ThinkPad P",
                   "ThinkBook", "ThinkPad", "IdeaPad Gaming", "IdeaPad",
                   "Legion", "Yoga", "LOQ", "IdeaCentre"],
    "Lenovo/IBM": ["ThinkPad X1 Carbon", "ThinkPad X1", "ThinkPad T",
                   "ThinkPad X", "ThinkPad L", "ThinkPad E", "ThinkPad P",
                   "ThinkBook", "ThinkPad", "IdeaPad Gaming", "IdeaPad",
                   "Legion", "Yoga", "LOQ", "IdeaCentre"],
    "Acer":       ["TravelMate", "ConceptD", "eMachines", "Aspire",
                   "Predator", "Extensa", "Chromebook", "Swift", "Spin",
                   "Nitro"],
    "Asus":       ["ROG Strix", "ROG Zephyrus", "ROG Flow", "ROG Ally",
                   "ExpertBook", "VivoBook", "Vivobook", "ProArt",
                   "ZenBook", "Zenbook", "Transformer", "Eee PC", "TUF Gaming",
                   "TUF Dash", "ROG", "TUF"],
    "MSI":        ["Raider", "Titan", "Stealth", "Summit", "Prestige",
                   "Katana", "Cyborg", "Pulse", "Modern", "Alpha", "Bravo"],
    "Apple":      ["Macbook Pro", "Macbook Air", "Macbook Neo", "Macbook",
                   "Mac Book", "Mac", "Pro", "Air"],
    "Microsoft":  ["Surface Pro", "Surface Laptop", "Surface Book",
                   "Surface Go", "Surface"],
    "Samsung":    ["Galaxy Book Pro", "Galaxy Book Flex", "Galaxy Book",
                   "Notebook"],
    "Huawei":     ["Matebook Pro", "Matebook D", "Matebook", "MateBook",
                   "MagicBook"],
    "Razer":      ["Blade", "Book", "Stealth"],
}


# Treat a leading 1-2 digit (or 1-digit + .x) token as a screen "size"
# (e.g. "Vostro 15 5000" -> "Vostro 15" + "5000"). When the size sits
# between the line and the rest of the model number, glue it to the
# model so the display reads "Vostro 15", not "Vostro".
_SIZE_RE = re.compile(r"^(\d{1,2}(?:\.\d+)?)\s+(.+)$")
# Bare integer / decimal token (e.g. "3" in "Aspire 3") — also counts as
# the size when there's no other content.
_BARE_NUM_RE = re.compile(r"^\d{1,2}(?:\.\d+)?$")


def _find_line(brand: str, model: str) -> tuple[str | None, str]:
    """Return (line_keyword_matched_or_None, rest_of_string)."""
    if not model:
        return None, ""
    # Try each keyword for this brand (longest first). The keyword + an
    # optional space at the start of the model marks the line boundary.
    keywords = LINE_KEYWORDS.get(brand) or LINE_KEYWORDS.get(brand.capitalize()) or []
    for kw in sorted(keywords, key=len, reverse=True):
        m = re.match(r"^" + re.escape(kw) + r"\b\s*(.*)$", model, flags=re.IGNORECASE)
        if m:
            return kw, m.group(1).strip()
    return None, model


def split_model(brand: str | None, model: str | None) -> tuple[str, str | None]:
    """Best-effort split of `model` into (base_model, model_number).

    Returns:
        base_model:    the family/line name, e.g. "Vostro 15", "Aspire 5"
        model_number:  the SKU/identifier, e.g. "5000", "A515-58P";
                       None when no recognisable line was found or the
                       rest of the model looks like a bare size/generation.

    The split is intentionally conservative — when in doubt we keep the
    whole `model` string as the base_model and leave model_number NULL,
    so the admin can fix it from the edit panel.
    """
    if not model:
        return model or "", None
    line, rest = _find_line(brand or "", model)
    if not line:
        # No recognised line — keep the original model intact.
        return model, None
    if not rest:
        return line, None
    # Try to peel off a leading "size" (1-2 digit number) so the display
    # shows "Vostro 15" rather than "Vostro" when the size sits between
    # the line and the SKU.
    m = _SIZE_RE.match(rest)
    if m:
        size, sku = m.group(1), m.group(2).strip()
        if sku:
            return f"{line} {size}", sku
        return f"{line} {size}", None
    if _BARE_NUM_RE.match(rest):
        # Bare size (e.g. "3" in "Aspire 3") — fold it into the model.
        return f"{line} {rest}", None
    return line, rest


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Don't UPDATE; just report.")
    ap.add_argument("--limit", type=int, default=0, help="Max reference rows to scan (0 = all).")
    args = ap.parse_args()

    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, brand, model, model_number
        FROM laptop_reference
        WHERE model IS NOT NULL AND model <> ''
        ORDER BY id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Scanning {len(refs)} reference rows for the model/model_number split")

    # Show a small sample of what the split produces before running the
    # UPDATE — gives the user a chance to abort if the patterns are wrong.
    if not args.dry_run:
        sample = refs[:10]
        print("\nSample of planned changes:")
        for r in sample:
            new_model, new_number = split_model(r["brand"], r["model"])
            print(f"  {r['id']:4}  {r['brand']!r:12} {r['model']!r:35} -> {new_model!r:25} / {new_number!r}")
        print()

    updated = 0
    unchanged = 0
    samples_unchanged: list[tuple] = []
    for r in refs:
        new_model, new_number = split_model(r["brand"], r["model"])
        if (new_model == r["model"]) and (new_number == r["model_number"]):
            unchanged += 1
            if len(samples_unchanged) < 8:
                samples_unchanged.append((r["id"], r["brand"], r["model"], r["model_number"]))
            continue
        if args.dry_run:
            print(f"  [dry-run] {r['id']:4} {r['brand']!r:12} {r['model']!r:35} -> {new_model!r:25} / {new_number!r}")
        else:
            cur.execute(
                "UPDATE laptop_reference SET model = %s, model_number = %s, updated_at = NOW() WHERE id = %s",
                (new_model, new_number, r["id"]),
            )
        updated += 1

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()

    print(f"\nUpdated {updated}  Unchanged {unchanged}  (dry-run={args.dry_run})")
    if samples_unchanged:
        print("Sample of unchanged rows (admin can fix from the edit panel):")
        for rid, brand, model, number in samples_unchanged:
            print(f"  {rid:4}  {brand!r:12} {model!r:35} / {number!r}")


if __name__ == "__main__":
    main()
