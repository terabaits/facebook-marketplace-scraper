import requests
import re
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu' LIMIT 3")
rows = cur.fetchall()

for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent':'Mozilla/5.0'})
        text = resp.text
        # find image gallery URLs like https://i.ss.com/gallery/...
        imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', text)
        # find message id in page (often in meta or links)
        msg_ids = re.findall(r'/msg/(\d{6,10})/', text) + re.findall(r'msg_id[=:](\d{6,10})', text, re.I)
        print('---', lid, resp.status_code, '---')
        print('url:', url)
        print('msg_ids:', sorted(set(msg_ids))[:5])
        print('imgs:', imgs[:3])
    except Exception as e:
        print('ERR', lid, e)

cur.close(); conn.close()
