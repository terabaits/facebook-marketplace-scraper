"""Backfill `laptop_reference.model_number` from existing listing descriptions.

Mirrors the refresh-rate backfill: walks every `laptop_reference` row whose
`model_number` is still NULL and looks for SKU-like patterns in the linked
`laptop_listings.description` values. The most common match across the
group is written to `model_number`.

Patterns we recognise:
    * `A515-58P` / `A515/51G`     — letter-prefixed model with optional dash sub-id
    * `UX425`, `FX506`, `G513`    — letter-prefixed SKUs common on Asus/MSI
    * `5520U`, `1135G7`, `7400U`   — digit-prefixed SKUs (Dell / Intel naming)
    * `T14`, `X13`, `A1466`        — short letter+digit combos (Lenovo / Apple internal)

Admin can refine anything the script gets wrong from the edit panel. Safe
to re-run.

Usage (from SS-CRAWLER root, with the venv active):

    python backfill_laptop_reference_model_from_description.py --dry-run
    python backfill_laptop_reference_model_from_description.py
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor


# Candidate SKU regexes. Each one is anchored on a word boundary so we
# don't accidentally match inside long tokens. We collect every match
# across the group's descriptions and pick the most common one.
_SKU_PATTERNS = [
    # Letter-prefixed with optional dash sub-id: A515, A515-58P, A515/51G
    re.compile(r"\b([A-Z]{1,2}\d{3,5})(?:[-/](\d{1,3}[A-Z]?))?\b", re.IGNORECASE),
    # Digit-prefixed SKU with 1-3 letter suffix: 5520U, 1135G7, 7400U
    re.compile(r"\b(\d{4,5}[A-Z]{1,3})\b", re.IGNORECASE),
    # Short letter+digit combos: G7, T14, X13, M15, A1466
    re.compile(r"\b([A-Z]\d{1,4}[A-Z]?)\b", re.IGNORECASE),
]

# Tokens that look like SKUs but are too common / ambiguous — skip these
# even if the regex matches. Keeps the backfill conservative.
_FALSE_POSITIVES = {
    # CPU families / series letters
    "I3", "I5", "I7", "I9", "M1", "M2", "M3", "M4", "M5",
    "X1", "X2", "X3", "X4", "X5",
    # Common words that look like SKUs
    "OK", "IT", "ID", "TV", "PC", "GB", "TB", "USD", "EUR",
    "HD", "SD", "USB", "RAM", "SSD", "HDD", "HDMI", "WIFI",
    "W11", "W10", "WIN11", "WIN10",
    # Year-ish numbers
    "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025",
    # Common size-like numbers
    "13", "14", "15", "16", "17", "12",
}

# CPU model numbers look like "12450H", "1135G7", "5500U", "4600H" — 4-5
# digits with a CPU-suffix letter at the end. They're not laptop SKUs, so
# skip them. The heuristic is: starts with 1-7 (Intel 10th-14th / AMD
# Ryzen 1000-7000 series), then 3-4 digits, then 1-2 letters.
_CPU_MODEL_RE = re.compile(r"^[1-7]\d{3,4}[A-Z]{1,2}$")


def _is_cpu_model(sku: str) -> bool:
    return bool(_CPU_MODEL_RE.match(sku))


def extract_candidate_skus(description: str) -> list[str]:
    """Return all plausible SKUs found in `description`."""
    if not description:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for pat in _SKU_PATTERNS:
        for m in pat.finditer(description):
            # For the first pattern, the captured group already includes
            # the optional dash-sub-id — reassemble if present.
            groups = m.groups()
            sku = groups[0]
            if len(groups) > 1 and groups[1]:
                sku = f"{groups[0]}-{groups[1]}"
            sku = sku.upper()
            if sku in _FALSE_POSITIVES or _is_cpu_model(sku) or sku in seen:
                continue
            seen.add(sku)
            out.append(sku)
    return out


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
        SELECT lr.id, lr.brand, lr.model, lr.display_size
        FROM laptop_reference lr
        WHERE lr.model_number IS NULL
        ORDER BY lr.id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Scanning {len(refs)} reference rows with NULL model_number")

    updated = 0
    skipped = 0
    samples_updated: list[tuple] = []
    for r in refs:
        cur.execute("""
            SELECT description FROM laptop_listings
            WHERE brand = %s AND model = %s
              AND (display_size IS NOT DISTINCT FROM %s)
              AND description IS NOT NULL
        """, (r["brand"], r["model"], r["display_size"]))
        descs = [row["description"] for row in cur.fetchall()]
        # Most-common SKU across the group's descriptions
        cands: Counter = Counter()
        for d in descs:
            for sku in extract_candidate_skus(d):
                cands[sku] += 1
        if not cands:
            skipped += 1
            continue
        best, _hits = cands.most_common(1)[0]
        if args.dry_run:
            print(f"  [dry-run] {r['id']:4} {r['brand']!r:12} {r['model']!r:30} -> {best!r}  (cands: {dict(cands)})")
        else:
            cur.execute(
                "UPDATE laptop_reference SET model_number = %s, updated_at = NOW() WHERE id = %s",
                (best, r["id"]),
            )
        updated += 1
        if len(samples_updated) < 8:
            samples_updated.append((r["id"], r["brand"], r["model"], best, dict(cands)))

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()
    print(f"\nUpdated {updated}  Skipped (no match) {skipped}  (dry-run={args.dry_run})")
    if samples_updated:
        print("Sample of updated rows:")
        for rid, brand, model, best, cands in samples_updated:
            print(f"  {rid:4}  {brand!r:12} {model!r:30} -> {best!r}  (cands: {cands})")


if __name__ == "__main__":
    main()
