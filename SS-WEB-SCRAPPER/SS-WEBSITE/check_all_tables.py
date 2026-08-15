import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check ALL tables for columns that might match
print("=== Checking all tables ===")
cursor.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    cursor.execute(f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{table}'
    """)
    cols = [row[0] for row in cursor.fetchall()]
    if 'id' in cols or 'lens' in str(cols).lower():
        print(f"\n{table}: {cols}")

cursor.close()
conn.close()
