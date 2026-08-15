"""Peek at the actual laptop_reference model values per brand so we can
design the model/model_number split with realistic patterns."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-CRAWLER"))

import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                        user="crawler", password="crawler_pass")
cur = conn.cursor()

cur.execute("""
    SELECT brand, model, COUNT(*) AS n
    FROM laptop_reference
    WHERE model IS NOT NULL AND model <> ''
    GROUP BY brand, model
    ORDER BY brand, n DESC
""")

current_brand = None
for brand, model, n in cur.fetchall():
    if brand != current_brand:
        print(f"\n=== {brand!r} ===")
        current_brand = brand
    print(f"  {n:4}  {model!r}")

cur.close()
conn.close()
