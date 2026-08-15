import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check for RAM ID 18
cursor.execute("""
    SELECT id, name, capacity_gb, type 
    FROM ram_reference 
    WHERE id = 18
""")
row = cursor.fetchone()
print(f"RAM ID 18: {row}")

# Check listings with RAM ID 18
cursor.execute("""
    SELECT COUNT(*) 
    FROM listings 
    WHERE matched_ram_id = 18 AND price_eur > 0
""")
count = cursor.fetchone()[0]
print(f"Listings with RAM ID 18: {count}")

# Check ALL RAM listings
cursor.execute("""
    SELECT 
        r.id,
        r.name,
        COUNT(l.listing_id) as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
    FROM ram_reference r
    LEFT JOIN listings l ON r.id = l.matched_ram_id AND l.price_eur > 0
    WHERE r.capacity_gb = 32 AND r.type = 'DDR5'
    GROUP BY r.id, r.name
    ORDER BY listing_count DESC
    LIMIT 5
""")
print("\n32GB DDR5 RAM models with listings:")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} - {row[2]} listings, avg €{row[3]}")

cursor.close()
conn.close()
