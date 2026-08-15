import os, re, requests, hashlib, psycopg2
from PIL import Image
from io import BytesIO
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu' AND local_image_path IS NULL")
rows = cur.fetchall()

files = {f: os.path.join(PSU_DIR, f) for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))}

def get_hash(path_or_bytes, size=(32,32)):
    try:
        if isinstance(path_or_bytes, str):
            img = Image.open(path_or_bytes)
        else:
            img = Image.open(BytesIO(path_or_bytes))
        return list(img.convert('L').resize(size).getdata())
    except Exception:
        return None

def sim(a,b):
    if not a or not b or len(a)!=len(b): return 0
    return sum(1 for x,y in zip(a,b) if abs(x-y)<15) / len(a)

local_hashes = {f: get_hash(p) for f,p in files.items()}

updates = []
for r in rows:
    lid = r['listing_id']; url = r['listing_url']
    try:
        text = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'}).text
        img_urls = sorted(set(re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', text)))
        best = None; best_score = 0
        for iu in img_urls:
            rh = get_hash(requests.get(iu, timeout=25, headers={'User-Agent':'Mozilla/5.0'}).content)
            if not rh: continue
            for f, lh in local_hashes.items():
                if not lh: continue
                s = sim(rh, lh)
                if s > best_score:
                    best_score = s; best = f
        print(lid, 'best', best, 'score', round(best_score,3))
        if best and best_score > 0.75:
            updates.append((lid, 'psu/' + best))
    except Exception as e:
        print('ERR', lid, e)

print('updates', len(updates))
if updates:
    cur.executemany("UPDATE listings SET local_image_path=%s WHERE listing_id=%s", [(p, lid) for lid,p in updates])
    conn.commit()
    print('DB updated')

cur.close(); conn.close()
