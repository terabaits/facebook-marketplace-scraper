import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check RAM category stats
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
print(f"RAM Stats: total={row[0]}, active={row[1]}, matched={row[2]}, unmatched={row[3]}, avg_price={row[4]}")

# Check all categories
cursor.execute("""
    SELECT category, COUNT(*) 
    FROM listings 
    GROUP BY category 
    ORDER BY category
""")
print("\nAll categories:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

cursor.close()
conn.close()
