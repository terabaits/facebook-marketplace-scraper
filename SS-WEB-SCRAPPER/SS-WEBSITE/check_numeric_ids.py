import psycopg2
from psycopg2.extras import RealDictCursor
import re

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)

print('PSU listing_ids with digits:')
cur.execute("SELECT listing_id FROM listings WHERE category='psu'")
for row in cur.fetchall():
    lid = row['listing_id']
    if re.search(r'\d', lid):
        print(lid)

cur.close(); conn.close()
