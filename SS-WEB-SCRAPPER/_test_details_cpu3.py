"""Verify /api/listing-details returns the normalized CPU fields in `current`."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2

from app import app


def main() -> None:
    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT ll.listing_id, ll.cpu_raw, lrc.brand, lrc.model
        FROM laptop_listings ll
        JOIN laptop_reference_cpu lrc ON lrc.id = ll.cpu_reference_id
        ORDER BY random()
        LIMIT 12
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    client = app.test_client()
    print(f"Testing {len(rows)} listings via /api/listing-details")
    print()
    n_ok = n_mismatch = 0
    for listing_id, raw, brand, model in rows:
        resp = client.get(f"/api/listing-details/{listing_id}")
        data = json.loads(resp.data)
        cur = data.get("current") or {}
        api_brand = cur.get("cpu_brand_normalized")
        api_model = cur.get("cpu_model_normalized")
        ok = (api_brand == brand and api_model == model)
        flag = "OK  " if ok else "FAIL"
        print(f"  [{flag}] {listing_id:10}  raw={raw!r:30}  db={brand!r:8} {model!r:20}  api={api_brand!r:8} {api_model!r}")
        if ok:
            n_ok += 1
        else:
            n_mismatch += 1
    print()
    print(f"  {n_ok} OK, {n_mismatch} mismatched")


if __name__ == "__main__":
    main()
