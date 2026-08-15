import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check normalized_name
print("=== Sample normalized_name values ===")
cursor.execute("""
    SELECT normalized_name FROM lens_reference 
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}'")

# Check if any match
print("\n=== Checking if matched_lens_id matches normalized_name ===")
cursor.execute("""
    SELECT COUNT(*) 
    FROM listings l
    WHERE l.category = 'lens' 
    AND l.matched_lens_id IS NOT NULL
    AND EXISTS (SELECT 1 FROM lens_reference lr WHERE lr.normalized_name = l.matched_lens_id)
""")
print(f"Listings with matching normalized_name: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
