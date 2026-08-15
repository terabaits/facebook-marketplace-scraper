import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check all columns in lens_reference
print("=== lens_reference columns ===")
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'lens_reference'
""")
columns = [row[0] for row in cursor.fetchall()]
print(columns)

# Check a few full rows
print("\n=== Sample lens_reference rows ===")
cursor.execute("""
    SELECT * FROM lens_reference 
    LIMIT 3
""")
rows = cursor.fetchall()
for row in rows:
    for i, col in enumerate(columns):
        print(f"  {col}: {row[i]}")
    print("---")

cursor.close()
conn.close()
