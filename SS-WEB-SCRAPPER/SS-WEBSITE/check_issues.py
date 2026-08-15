import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check RAM stats (what dashboard shows)
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

# Check motherboard confidence scores
print("\nMotherboard confidence score distribution:")
cursor.execute("""
    SELECT 
        CASE 
            WHEN motherboard_confidence_score IS NULL THEN 'NULL'
            WHEN motherboard_confidence_score < 0.5 THEN '< 0.5'
            WHEN motherboard_confidence_score < 0.7 THEN '0.5-0.7'
            ELSE '>= 0.7'
        END as score_range,
        COUNT(*)
    FROM listings 
    WHERE category = 'motherboard'
    GROUP BY 1
    ORDER BY 1
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} listings")

cursor.close()
conn.close()
