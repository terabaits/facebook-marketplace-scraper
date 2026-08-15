import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Test the exact query from app.py
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
print(f"Direct query result: {row}")
print(f"Type: {type(row)}")

# Check if matched_ram_id column exists
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'listings' AND column_name = 'matched_ram_id'
""")
result = cursor.fetchone()
print(f"matched_ram_id column exists: {result is not None}")

cursor.close()
conn.close()
