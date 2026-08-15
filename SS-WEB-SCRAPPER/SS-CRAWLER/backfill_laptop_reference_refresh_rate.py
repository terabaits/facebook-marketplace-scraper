"""Backfill `laptop_reference.refresh_rate_hz` from existing listing descriptions.

Two passes:
1. Walk every `laptop_reference` row and use the most common refresh rate
   found in the matching `laptop_listings.description` values. When the
   description has a Hz value, use it.
2. Any rows still NULL after pass 1 get the industry default of 60 Hz
   (since the vast majority of panels are 60 Hz when the seller doesn't
   bother to mention the rate).

Safe to re-run.

Usage (from SS-CRAWLER root, with the venv active):

    python backfill_laptop_reference_refresh_rate.py --dry-run
    python backfill_laptop_reference_refresh_rate.py
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor

# Reuse the resolver's extraction (after the 60Hz default change, the
# helper returns 60 when no Hz is found, so we only count non-60 matches
# in pass 1 and rely on pass 2 for the default).
_REFRESH_RATE_PATTERN = __import__("re").compile(
    r"(?<![A-Za-z0-9])(\d{2,3})\s*[Hh][Zz]\b"
)


def _extract_explicit_hz(description: str) -> int | None:
    """Return Hz only if the description has an explicit "NHz" / "N Hz"
    mention that passes the sanity check (30-1000). Returns None when no
    explicit Hz is present — the resolver would default to 60 for these."""
    if not description:
        return None
    m = _REFRESH_RATE_PATTERN.search(description)
    if not m:
        return None
    n = int(m.group(1))
    if not 30 <= n <= 1000:
        return None
    return n


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
        WHERE lr.refresh_rate_hz IS NULL
        ORDER BY lr.id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Pass 1: scanning {len(refs)} reference rows with NULL refresh_rate_hz")

    updated_explicit = 0
    updated_default = 0
    no_explicit_match = 0
    for r in refs:
        cur.execute("""
            SELECT description FROM laptop_listings
            WHERE brand = %s AND model = %s
              AND (display_size IS NOT DISTINCT FROM %s)
              AND description IS NOT NULL
        """, (r["brand"], r["model"], r["display_size"]))
        descs = [row["description"] for row in cur.fetchall()]
        # Pass 1: most common explicit Hz in the group's descriptions
        rates = Counter()
        for d in descs:
            hz = _extract_explicit_hz(d)
            if hz is not None:
                rates[hz] += 1
        if rates:
            best = rates.most_common(1)[0][0]
            if args.dry_run:
                print(f"  [dry-run] {r['id']:4} {r['brand']!r:12} {r['model']!r:30} -> {best}Hz (matches: {dict(rates)})")
            else:
                cur.execute(
                    "UPDATE laptop_reference SET refresh_rate_hz = %s, updated_at = NOW() WHERE id = %s",
                    (best, r["id"]),
                )
            updated_explicit += 1
        else:
            # Pass 2: default to 60 Hz (industry standard for unlabelled
            # laptop panels — covers the vast majority of machines).
            no_explicit_match += 1
            if args.dry_run:
                print(f"  [dry-run] {r['id']:4} {r['brand']!r:12} {r['model']!r:30} -> 60Hz (default)")
            else:
                cur.execute(
                    "UPDATE laptop_reference SET refresh_rate_hz = 60, updated_at = NOW() WHERE id = %s",
                    (r["id"],),
                )
            updated_default += 1

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()
    print(f"\nUpdated {updated_explicit} (explicit Hz) + {updated_default} (default 60Hz) = {updated_explicit + updated_default}  (dry-run={args.dry_run})")


if __name__ == "__main__":
    main()
