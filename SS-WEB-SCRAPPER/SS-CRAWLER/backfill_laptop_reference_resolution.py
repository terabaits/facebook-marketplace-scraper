"""Backfill `laptop_reference.resolution` for rows that are still NULL.

The original migration (`migrations/create_laptop_reference_table.sql`) only
fills resolution when the regex match is unambiguous per group; a lot of
groups end up NULL. This script walks every NULL row and uses the Python
resolver's regex to pick the most-frequent WxH match across the group's
listings. Safe to re-run.

Usage (from SS-CRAWLER root, with the venv active):

    python backfill_laptop_reference_resolution.py [--dry-run] [--limit N]

The default is to update everything; pass --dry-run to print what would change.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Make the project importable when run as a script
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.scraper.laptop_reference_resolver import _DISPLAY_SIZE_RE  # noqa: E402

# Reuse the same regex as the resolver; keep them in sync if you change it.
# This one captures the two halves for group-by frequency analysis.
_RESOLUTION_FULL_RE = re.compile(r"(\d{3,4})\s*[x×]\s*(\d{3,4})")


def most_common_resolution(descriptions: list[str]) -> str | None:
    """Return the most-frequent WxH pattern across a list of descriptions, in
    canonical "WxH" form. None when no matches at all."""
    counter: Counter = Counter()
    for d in descriptions:
        if not d:
            continue
        m = _RESOLUTION_FULL_RE.search(d)
        if m:
            counter[f"{m.group(1)}x{m.group(2)}"] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Don't UPDATE; just report.")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to update (0 = all).")
    args = ap.parse_args()

    conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                            user="crawler", password="crawler_pass")
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Find reference rows that still have no resolution
    cur.execute("""
        SELECT lr.id, lr.brand, lr.model, lr.display_size
        FROM laptop_reference lr
        WHERE lr.resolution IS NULL OR lr.resolution = ''
        ORDER BY lr.id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Found {len(refs)} reference rows with NULL resolution")

    updated = 0
    skipped = 0
    for r in refs:
        cur.execute("""
            SELECT description FROM laptop_listings
            WHERE brand = %s AND model = %s
              AND (display_size IS NOT DISTINCT FROM %s)
              AND description IS NOT NULL
        """, (r["brand"], r["model"], r["display_size"]))
        descs = [row["description"] for row in cur.fetchall()]
        best = most_common_resolution(descs)
        if not best:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [dry-run] {r['id']:4} {r['brand']!r:12} {r['model']!r:30} -> {best}")
        else:
            cur.execute(
                "UPDATE laptop_reference SET resolution = %s, updated_at = NOW() WHERE id = %s",
                (best, r["id"]),
            )
        updated += 1

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()
    print(f"Updated {updated}  Skipped (no match) {skipped}  (dry-run={args.dry_run})")


if __name__ == "__main__":
    main()
