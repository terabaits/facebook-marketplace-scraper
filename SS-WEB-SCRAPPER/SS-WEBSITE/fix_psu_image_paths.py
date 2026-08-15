import os
import re
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu'")
rows = cur.fetchall()

files = {f: os.path.getsize(os.path.join(PSU_DIR, f)) for f in os.listdir(PSU_DIR)
         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))}
size_to_files = {}
for f, sz in files.items():
    size_to_files.setdefault(sz, []).append(f)

updates = []
for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    try:
        resp = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', resp.text)
        imgs = sorted(set(imgs))
        matched = None
        for img_url in imgs:
            try:
                img_resp = requests.get(img_url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
                sz = len(img_resp.content)
                if sz in size_to_files:
                    # verify first few bytes / hash
                    for cand in size_to_files[sz]:
                        with open(os.path.join(PSU_DIR, cand), 'rb') as fh:
                            local_content = fh.read()
                        if local_content == img_resp.content:
                            matched = cand
                            break
                    if matched:
                        break
            except Exception as e:
                print('ERR download', img_url, e)
                continue
        print(lid, 'matched:', matched)
        if matched:
            updates.append((lid, 'psu/' + matched))
    except Exception as e:
        print('ERR fetch', lid, e)

print('Total updates:', len(updates))
if updates:
    cur.executemany("UPDATE listings SET local_image_path=%s WHERE listing_id=%s", [(p, lid) for lid, p in updates])
    conn.commit()
    print('Database updated.')

cur.close()
conn.close()
