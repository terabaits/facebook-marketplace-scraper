import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check price_history columns
print("=== price_history columns ===")
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'price_history'
    ORDER BY ordinal_position
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
