"""Backfill `laptop_reference_cpu` and `laptop_listings.cpu_reference_id`
from the existing `cpu_raw` values in `laptop_listings`.

Reads every `cpu_raw` in `laptop_listings`, normalizes it via
`CPUReferenceResolver.normalize_cpu_name()`, and UPSERTs the row into
`laptop_reference_cpu` (UNIQUE on `normalized_key`). Then backfills
`laptop_listings.cpu_reference_id` with the FK.

Safe to re-run. Listings with NULL or un-parseable `cpu_raw` are left with
`cpu_reference_id = NULL` so the spec window can fall back to `cpu_raw`.

Usage (from SS-CRAWLER root, with the venv active):

    python backfill_laptop_reference_cpu.py --dry-run   # preview
    python backfill_laptop_reference_cpu.py             # apply
    python backfill_laptop_reference_cpu.py --limit 50  # first 50 listings only
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

# Make the project importable when run as a script
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.scraper.cpu_reference_resolver import normalize_cpu_name  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Don't write; just report.")
    ap.add_argument("--limit", type=int, default=0, help="Max listings to scan (0 = all).")
    ap.add_argument(
        "--verbose", action="store_true", help="Print every listing's resolution.",
    )
    args = ap.parse_args()

    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Pull every listing's raw CPU. Listings with NULL/empty cpu_raw or with
    # an already-resolved FK are skipped (we only fill the gap).
    cur.execute("""
        SELECT id, listing_id, cpu_raw, cpu_reference_id
        FROM laptop_listings
        WHERE cpu_raw IS NOT NULL AND TRIM(cpu_raw) <> ''
        ORDER BY id
    """)
    rows = cur.fetchall()
    if args.limit:
        rows = rows[: args.limit]
    print(f"Scanning {len(rows)} listings with non-empty cpu_raw")

    # 1) Walk every listing, normalize, accumulate what we'd write.
    #    We keep a small in-memory cache so the same normalized_key doesn't
    #    hit the DB UPSERT path multiple times.
    fk_updates = []           # (listing_db_id, cpu_reference_id) tuples
    unique_keys: dict[str, tuple[str, str]] = {}  # key -> (brand, model)
    skipped_no_match = 0
    skipped_already_resolved = 0
    unparseable_counter: Counter = Counter()
    sample_unparseable: list[str] = []

    for r in rows:
        if r["cpu_reference_id"] is not None:
            skipped_already_resolved += 1
            continue
        brand, model, key = normalize_cpu_name(r["cpu_raw"])
        if not key or not model or not brand:
            skipped_no_match += 1
            unparseable_counter[r["cpu_raw"]] += 1
            if len(sample_unparseable) < 10:
                sample_unparseable.append(r["cpu_raw"])
            if args.verbose:
                print(f"  [skip] {r['listing_id']!r:20} cpu_raw={r['cpu_raw']!r}")
            continue
        unique_keys.setdefault(key, (brand, model))
        # We don't know the FK yet (it'll be assigned during the UPSERT step),
        # so we record (listing_db_id, key) and resolve the FK in a second pass.
        fk_updates.append((r["id"], key))
        if args.verbose:
            print(
                f"  [{brand}] {r['listing_id']!r:20} "
                f"{r['cpu_raw']!r:30} -> {model!r}  ({key})"
            )

    print(f"\nUnique normalized keys: {len(unique_keys)}")
    if args.verbose:
        for key, (brand, model) in sorted(unique_keys.items()):
            print(f"  {brand:10} {model:25}  {key}")

    if args.dry_run:
        print(f"\n[DRY-RUN] would write {len(unique_keys)} reference rows")
        print(f"[DRY-RUN] would update {len(fk_updates)} listing FK columns")
        print(f"[DRY-RUN] skipped (unparseable): {skipped_no_match}")
        print(f"[DRY-RUN] skipped (already resolved): {skipped_already_resolved}")
        if sample_unparseable:
            print(f"[DRY-RUN] sample unparseable cpu_raw: {sample_unparseable}")
        cur.close()
        conn.close()
        return

    # 2) UPSERT each unique (brand, model) into laptop_reference_cpu.
    new_refs = 0
    for key, (brand, model) in unique_keys.items():
        cur.execute(
            """
            INSERT INTO laptop_reference_cpu (brand, model, normalized_key)
            VALUES (%s, %s, %s)
            ON CONFLICT (normalized_key) DO UPDATE
                SET normalized_key = EXCLUDED.normalized_key
            RETURNING id
            """,
            (brand, model, key),
        )
        new_refs += 1
    print(f"UPSERTed {new_refs} reference rows")

    # 3) Build a key -> id map in one query, then UPDATE all listings in batch.
    cur.execute("SELECT id, normalized_key FROM laptop_reference_cpu")
    key_to_id = {r["normalized_key"]: r["id"] for r in cur.fetchall()}

    # Group listings by FK id to issue fewer UPDATEs.
    by_fk: dict[int, list[int]] = {}
    for listing_db_id, key in fk_updates:
        ref_id = key_to_id.get(key)
        if ref_id is None:
            # Shouldn't happen — we just wrote the row.
            skipped_no_match += 1
            continue
        by_fk.setdefault(ref_id, []).append(listing_db_id)

    updated = 0
    for ref_id, listing_ids in by_fk.items():
        cur.execute(
            """
            UPDATE laptop_listings
            SET cpu_reference_id = %s
            WHERE id = ANY(%s)
            """,
            (ref_id, listing_ids),
        )
        updated += len(listing_ids)
    conn.commit()

    print(f"Updated {updated} listing cpu_reference_id values")
    print(f"Skipped (unparseable cpu_raw): {skipped_no_match}")
    print(f"Skipped (already resolved): {skipped_already_resolved}")
    if sample_unparseable:
        print(f"Sample unparseable cpu_raw: {sample_unparseable}")
        top = unparseable_counter.most_common(10)
        print(f"Top unparseable: {top}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
