import sys
sys.path.insert(0, 'src')
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# List tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
print("Tables in database:")
for row in cur.fetchall():
    print(f"  {row[0]}")

cur.close()
conn.close()
