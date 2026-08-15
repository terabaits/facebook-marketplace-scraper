import requests, re
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu' LIMIT 5")
rows = cur.fetchall()

for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    resp = requests.get(url, timeout=15, headers={'User-Agent':'Mozilla/5.0'})
    text = resp.text
    # Look at title and meta
    title = re.search(r'<title>(.*?)</title>', text, re.S)
    print('---', lid)
    print('title:', title.group(1) if title else '-')
    # find all numbers in image srcs near gallery
    imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', text)
    for img in imgs[:3]:
        print('  img:', img)
    # find all 7-8 digit numbers in page
    nums = sorted(set(re.findall(r'\b(\d{7,8})\b', text)))
    print('page nums sample:', nums[:20])

cur.close(); conn.close()
