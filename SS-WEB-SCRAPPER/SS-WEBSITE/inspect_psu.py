import psycopg2
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT listing_id, image_url, listing_url FROM listings WHERE category='psu' LIMIT 5")
for r in cur.fetchall():
    print(dict(r))
cur.close(); conn.close()
