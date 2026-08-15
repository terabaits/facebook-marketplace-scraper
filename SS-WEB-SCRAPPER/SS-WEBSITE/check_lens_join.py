import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Test the join
print("=== Testing lens_reference JOIN ===")
cursor.execute("""
    SELECT COUNT(*) 
    FROM lens_reference lr
    JOIN listings l ON lr.lens_name = l.matched_lens_id
    WHERE l.category = 'lens' AND l.is_active = true
""")
print(f"Join count: {cursor.fetchone()[0]}")

# Check sample data
print("\n=== Sample matched_lens_id values ===")
cursor.execute("""
    SELECT DISTINCT matched_lens_id 
    FROM listings 
    WHERE category = 'lens' AND matched_lens_id IS NOT NULL
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}'")

print("\n=== Sample lens_name values ===")
cursor.execute("""
    SELECT lens_name FROM lens_reference 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}'")

# Check if any match
cursor.execute("""
    SELECT COUNT(*) 
    FROM listings l
    WHERE l.category = 'lens' 
    AND l.matched_lens_id IS NOT NULL
    AND EXISTS (SELECT 1 FROM lens_reference lr WHERE lr.lens_name = l.matched_lens_id)
""")
print(f"\nListings with matching lens_name: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
