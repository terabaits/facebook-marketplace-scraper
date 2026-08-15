import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check category values for RAM listings
cursor.execute("""
    SELECT DISTINCT category, COUNT(*)
    FROM listings
    WHERE matched_ram_id IS NOT NULL
    GROUP BY category
""")
print("Categories for RAM listings:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} listings")

# Check fallback query results
cursor.execute("""
    SELECT l.price_eur, l.category, r.name, r.capacity_gb, r.type
    FROM listings l
    JOIN ram_reference r ON l.matched_ram_id = r.id
    WHERE r.capacity_gb = 32
    AND r.type ILIKE '%DDR5%'
    AND l.price_eur > 0
    ORDER BY l.price_eur
    LIMIT 10
""")
print("\n32GB DDR5 listings (fallback query):")
for row in cursor.fetchall():
    print(f"  €{row[0]} | cat={row[1]} | {row[2]}")

cursor.close()
conn.close()
