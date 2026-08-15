"""Verify /api/listing-details returns the normalized CPU fields."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2

from app import app


def main() -> None:
    # Pick a few listings from the DB that have a cpu_reference_id, to
    # confirm the JOIN actually returns the normalized fields.
    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT ll.listing_id, ll.cpu_raw, lrc.brand, lrc.model
        FROM laptop_listings ll
        JOIN laptop_reference_cpu lrc ON lrc.id = ll.cpu_reference_id
        ORDER BY ll.id
        LIMIT 6
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    client = app.test_client()
    print(f"Testing {len(rows)} listings via /api/listing-details")
    print()
    for listing_id, raw, brand, model in rows:
        resp = client.get(f"/api/listing-details/{listing_id}")
        data = json.loads(resp.data)
        cpu_raw = data.get("cpu_raw")
        cpu_brand = data.get("cpu_brand_normalized")
        cpu_model = data.get("cpu_model_normalized")
        print(f"  listing={listing_id}")
        print(f"    cpu_raw:                {cpu_raw!r}")
        print(f"    cpu_brand_normalized:   {cpu_brand!r}")
        print(f"    cpu_model_normalized:   {cpu_model!r}")
        print(f"    DB expected:            {brand!r} {model!r}")
        ok = (cpu_brand == brand and cpu_model == model)
        print(f"    match: {'OK' if ok else 'MISMATCH'}")
        print()


if __name__ == "__main__":
    main()
