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

files = {f.lower(): f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))}
file_nums = {}
for lower_name, orig_name in files.items():
    m = re.match(r'(\d{6,10})_', lower_name)
    if m:
        file_nums.setdefault(m.group(1), []).append(orig_name)

updates = []
for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    matched = None
    try:
        resp = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'})
        img_nums = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', resp.text)
        for img in img_nums:
            m = re.search(r'(\d{6,10})\.[a-z0-9]+$', os.path.basename(img))
            if not m:
                continue
            num = m.group(1)
            if num in file_nums:
                matched = file_nums[num][0]
                break
    except Exception as e:
        print('ERR fetching', lid, e)
        continue
    print(lid, 'matched:', matched)
    if matched:
        updates.append((lid, 'psu/' + matched))

print('Total updates:', len(updates))
if updates:
    cur.executemany("UPDATE listings SET local_image_path=%s WHERE listing_id=%s", [(p, lid) for lid, p in updates])
    conn.commit()
    print('Database updated.')

cur.close(); conn.close()
