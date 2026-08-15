import psycopg2
from psycopg2.extras import RealDictCursor
import os, re

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)

print('=== PSUs image_url samples ===')
cur.execute("""
SELECT listing_id, image_url, local_image_path
FROM listings
WHERE category='psu'
LIMIT 30
""")
rows = cur.fetchall()
for row in rows:
    print(dict(row))

cur.close(); conn.close()

# Also list psu image files
print('\n=== PSU image files first 30 ===')
folder = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
for f in sorted(os.listdir(folder))[:30]:
    print(f)
