import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check distinct sources for GPU listings
print("=== GPU listings by source ===")
cursor.execute("""
    SELECT source, COUNT(*) 
    FROM listings 
    WHERE category = 'gpu'
    GROUP BY source
    ORDER BY COUNT(*) DESC
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check Facebook GPU listings specifically
print("\n=== Facebook GPU listings ===")
cursor.execute("""
    SELECT listing_id, title, price_eur, source
    FROM listings 
    WHERE category = 'gpu' AND source = 'facebook'
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1][:50]} | €{row[2]} | {row[3]}")

# Check what source values exist
print("\n=== All distinct source values ===")
cursor.execute("""
    SELECT DISTINCT source
    FROM listings 
    WHERE category = 'gpu'
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}'")

cursor.close()
conn.close()
