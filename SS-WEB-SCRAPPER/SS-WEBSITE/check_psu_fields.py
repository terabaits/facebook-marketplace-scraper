import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)

print('=== PSU listings with relevant fields ===')
cur.execute("""
SELECT listing_id, title, listing_url, image_url, local_image_path, source
FROM listings
WHERE category='psu'
LIMIT 30
""")
for row in cur.fetchall():
    print(dict(row))

cur.close(); conn.close()
