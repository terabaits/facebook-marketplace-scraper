import os
import re
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url, title, description FROM listings WHERE category='psu'")
rows = cur.fetchall()

files = set(f.lower() for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp')))

updates = []
for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    try:
        resp = requests.get(url, timeout=20, headers={'User-Agent':'Mozilla/5.0'})
        imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', resp.text)
        imgs = sorted(set(imgs))
        # Look for image filename number in local files
        matched = None
        for img in imgs:
            base = os.path.basename(img)
            m = re.search(r'(\d{6,10})\.[a-z0-9]+$', base)
            if m:
                num = m.group(1)
                candidates = [f for f in files if f.startswith(num + '_')]
                if candidates:
                    matched = candidates[0]
                    break
        print(lid, 'imgs:', len(imgs), 'matched:', matched)
        if matched:
            updates.append((lid, 'psu/' + matched))
    except Exception as e:
        print('ERR', lid, e)

print('updates:', len(updates))
for u in updates[:10]:
    print(u)

if updates:
    cur.executemany("UPDATE listings SET local_image_path=%s WHERE listing_id=%s", [(p, lid) for lid, p in updates])
    conn.commit()
    print('DB updated')

cur.close(); conn.close()
