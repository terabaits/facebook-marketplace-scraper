import os
import re
import requests
import hashlib
import psycopg2
from PIL import Image
from io import BytesIO
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu'")
rows = cur.fetchall()

files = [f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]

def image_hash(path, size=(16, 16)):
    try:
        with Image.open(path) as img:
            img = img.convert('L').resize(size)
            return list(img.getdata())
    except Exception as e:
        return None

local_hashes = {f: image_hash(os.path.join(PSU_DIR, f)) for f in files}

def remote_hash(url, size=(16, 16)):
    try:
        r = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        img = Image.open(BytesIO(r.content)).convert('L').resize(size)
        return list(img.getdata())
    except Exception as e:
        return None

def similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0
    diffs = sum(1 for x, y in zip(a, b) if abs(x - y) > 10)
    return 1 - diffs / len(a)

updates = []
for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    try:
        resp = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', resp.text)
        imgs = sorted(set(imgs))
        best = None
        best_score = 0
        for img_url in imgs:
            rh = remote_hash(img_url)
            if not rh:
                continue
            for f, lh in local_hashes.items():
                if not lh:
                    continue
                score = similarity(rh, lh)
                if score > best_score:
                    best_score = score
                    best = f
        print(lid, 'best match:', best, 'score:', round(best_score, 3))
        if best and best_score > 0.7:
            updates.append((lid, 'psu/' + best))
    except Exception as e:
        print('ERR', lid, e)

print('Total updates:', len(updates))
if updates:
    cur.executemany("UPDATE listings SET local_image_path=%s WHERE listing_id=%s", [(p, lid) for lid, p in updates])
    conn.commit()
    print('Database updated.')

cur.close()
conn.close()
