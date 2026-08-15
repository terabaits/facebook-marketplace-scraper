import os, re, requests, psycopg2
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Build a map from remote SS image URL to local file by downloading+hashing.
# Instead, since we have 136 files, just match the message ID extracted from the 
# listing page HTML. Previous attempts didn't match.  Let's enumerate the local
# file prefix numbers and also see if any file name appears in page source.

files = {f.lower(): f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))}
file_nums = {m.group(1): orig for orig in files for m in [re.match(r'(\d{6,10})_', orig.lower())] if m}
print('local file nums', len(file_nums))

cur.execute("SELECT listing_id, listing_url FROM listings WHERE category='psu'")
rows = cur.fetchall()
for r in rows:
    lid = r['listing_id']
    url = r['listing_url']
    resp = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'})
    # print all numbers present in page that are also local file nums
    nums = set(re.findall(r'\b(\d{7,8})\b', resp.text))
    inter = nums & set(file_nums.keys())
    print(lid, 'intersection', inter if inter else nums & set(file_nums.keys()))

cur.close(); conn.close()
