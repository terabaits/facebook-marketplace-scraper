import os
import re
import requests
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from io import BytesIO

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

def file_hash(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

files = [f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
file_hashes = {f: file_hash(os.path.join(PSU_DIR, f)) for f in files}
print('Hashed', len(file_hashes), 'local files')

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu'")
rows = cur.fetchall()

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
                remote_hash = hashlib.md5(img_resp.content).hexdigest()
                for fname, fhash in file_hashes.items():
                    if remote_hash == fhash:
                        matched = fname
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
