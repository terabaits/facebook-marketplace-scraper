import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check lens_reference columns
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'lens_reference'
    ORDER BY column_name
""")
print("lens_reference columns:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
