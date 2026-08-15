"""List laptop_reference rows matching the user's filter criteria."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                        user="crawler", password="crawler_pass")
cur = conn.cursor()
cur.execute("""
    SELECT lr.id, lr.brand, lr.model, lr.model_number, lr.display_size,
           COUNT(ll.id) AS listings
    FROM laptop_reference lr
    LEFT JOIN laptop_listings ll ON ll.laptop_reference_id = lr.id
    WHERE lr.brand != 'Apple'
      AND lr.model NOT LIKE '%TUF%'
      AND lr.model != 'Dash'
      AND lr.model != lr.model_number
      AND lr.model_number NOT IN ('G3', 'G6', 'g4')
      AND lr.model_number IS NOT NULL
    GROUP BY lr.id, lr.brand, lr.model, lr.model_number, lr.display_size
    ORDER BY lr.brand, lr.model
""")
rows = cur.fetchall()
print(f"Matched {len(rows)} reference rows:")
print()
print(f"  {'ID':>4}  {'brand':12}  {'model':25}  {'model_number':18}  {'size':>5}  {'listings':>4}")
print("  " + "-" * 80)
for r in rows:
    size = r[4] or ""
    print(f"  {r[0]:>4}  {r[1][:12]:12}  {r[2][:25]:25}  {r[3][:18]:18}  {size:>5}  {r[5]:>4}")
cur.close()
conn.close()
