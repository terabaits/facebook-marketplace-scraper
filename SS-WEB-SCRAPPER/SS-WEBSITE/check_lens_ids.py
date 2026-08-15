import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check lens ID format
cursor.execute("""
    SELECT DISTINCT matched_lens_id 
    FROM listings 
    WHERE category = 'lens' AND matched_lens_id IS NOT NULL
    LIMIT 5
""")
print("Sample matched_lens_id values:")
for row in cursor.fetchall():
    print(f"  '{row[0]}' (type: {type(row[0])})")

# Check lens_reference IDs
cursor.execute("""
    SELECT id FROM lens_reference LIMIT 5
""")
print("\nSample lens_reference IDs:")
for row in cursor.fetchall():
    print(f"  '{row[0]}' (type: {type(row[0])})")

cursor.close()
conn.close()
