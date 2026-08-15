import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check ALL distinct matched_lens_id values
print("=== All distinct matched_lens_id values ===")
cursor.execute("""
    SELECT DISTINCT matched_lens_id 
    FROM listings 
    WHERE category = 'lens' AND matched_lens_id IS NOT NULL
    ORDER BY matched_lens_id
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}'")

# Check if there's a scraper_lookup or similar table
print("\n=== Checking for lookup tables ===")
cursor.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name LIKE '%lookup%' OR table_name LIKE '%scrape%' OR table_name LIKE '%map%'
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Check lens_reference for any columns that might match
print("\n=== Checking lens_reference for ID-like columns ===")
cursor.execute("""
    SELECT id, lens_name, normalized_name 
    FROM lens_reference 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  id={row[0]}, lens_name='{row[1]}', normalized_name='{row[2]}'")

cursor.close()
conn.close()
