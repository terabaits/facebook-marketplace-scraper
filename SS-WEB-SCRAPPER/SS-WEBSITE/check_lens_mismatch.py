import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check all lens_reference lens_name values to see if any match
print("=== Checking if ANY lens_name matches ===")
cursor.execute("""
    SELECT lens_name FROM lens_reference 
    WHERE lens_name LIKE '%Canon%50%'
""")
print("Canon 50mm-like lenses:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Check if the issue is the scraped data format
print("\n=== Sample listings titles ===")
cursor.execute("""
    SELECT title, matched_lens_id 
    FROM listings 
    WHERE category = 'lens' AND matched_lens_id IS NOT NULL
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  Title: {row[0]}")
    print(f"  matched_lens_id: {row[1]}")
    print()

cursor.close()
conn.close()
