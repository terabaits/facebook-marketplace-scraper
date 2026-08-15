import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check for any table that might map between these formats
print("=== Checking for mapping tables ===")
cursor.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public'
    AND table_name LIKE '%lens%'
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Check normalized_name patterns
print("\n=== Checking normalized_name for canon 50mm ===")
cursor.execute("""
    SELECT normalized_name FROM lens_reference 
    WHERE normalized_name LIKE '%canon%50%'
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
