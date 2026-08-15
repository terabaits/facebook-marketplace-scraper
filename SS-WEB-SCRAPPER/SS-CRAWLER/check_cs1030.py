import sys
sys.path.insert(0, 'src')
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Check SSD ID 1381
cur.execute("SELECT id, brand, model, capacity_gb, search_keywords FROM ssd_reference WHERE id = 1381")
row = cur.fetchone()
if row:
    print(f"SSD ID 1381:")
    print(f"  Brand: {row[1]}")
    print(f"  Model: {row[2]}")
    print(f"  Capacity: {row[3]}GB")
    print(f"  Keywords: {row[4]}")

cur.close()
conn.close()
