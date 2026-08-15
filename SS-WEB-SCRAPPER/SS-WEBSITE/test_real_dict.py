import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

# Test with RealDictCursor (what app.py uses)
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute("""
    SELECT 
        COUNT(*) as total_listings,
        COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
        COUNT(CASE WHEN matched_ram_id IS NOT NULL THEN 1 END) as matched,
        COUNT(CASE WHEN matched_ram_id IS NULL THEN 1 END) as unmatched,
        ROUND(AVG(price_eur)::numeric, 2) as avg_price
    FROM listings 
    WHERE category = 'ram'
""")

row = cursor.fetchone()
print(f"RealDictCursor result type: {type(row)}")
print(f"RealDictCursor result: {row}")
print(f"dict(row): {dict(row)}")

# Check what the query actually returns
print(f"\nRow keys: {row.keys()}")
print(f"Row values: {list(row.values())}")

cursor.close()
conn.close()
