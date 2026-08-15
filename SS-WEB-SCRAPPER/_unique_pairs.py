"""List the unique (brand, combined_query) pairs to look up."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                        user="crawler", password="crawler_pass")
cur = conn.cursor()
cur.execute("""
    SELECT lr.brand, lr.model, lr.model_number, lr.id
    FROM laptop_reference lr
    WHERE lr.brand != 'Apple'
      AND lr.model NOT LIKE '%TUF%'
      AND lr.model != 'Dash'
      AND lr.model != lr.model_number
      AND lr.model_number NOT IN ('G3', 'G6', 'g4')
      AND lr.model_number IS NOT NULL
    ORDER BY lr.brand, lr.model, lr.model_number
""")
rows = cur.fetchall()
# Group by (brand, combined)
from collections import defaultdict
by_brand = defaultdict(list)
seen = set()
for brand, m, n, rid in rows:
    combined = f"{(m or '').strip()} {(n or '').strip()}".strip()
    key = (brand, combined.lower())
    if key in seen:
        continue
    seen.add(key)
    by_brand[brand].append((combined, rid))

for brand, items in sorted(by_brand.items()):
    print(f"\n=== {brand} ({len(items)} unique) ===")
    for combined, rid in items[:60]:
        print(f"  [id={rid}]  {combined}")
    if len(items) > 60:
        print(f"  ... and {len(items) - 60} more")
print(f"\nTotal unique pairs: {len(seen)}")
cur.close()
conn.close()
