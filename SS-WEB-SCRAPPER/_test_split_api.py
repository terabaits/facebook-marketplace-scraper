"""Verify the model/model_number split is exposed in the API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2
import json

import app as app_module
client = app_module.app.test_client()

conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                        user="crawler", password="crawler_pass")
cur = conn.cursor()
cur.execute("""
    SELECT ll.listing_id, lr.model, lr.model_number
    FROM laptop_listings ll
    JOIN laptop_reference lr ON lr.id = ll.laptop_reference_id
    WHERE lr.model_number IS NOT NULL
    ORDER BY ll.id
    LIMIT 8
""")
print("Test listings with model_number populated:")
for listing_id, db_model, db_number in cur.fetchall():
    r = client.get(f"/api/listing-details/{listing_id}")
    d = json.loads(r.data)
    c = d.get("current") or {}
    print(f"  {listing_id}  db=({db_model!r}, {db_number!r})  api=({c.get('laptop_model')!r}, {c.get('laptop_model_number')!r})")

cur.close()
conn.close()
