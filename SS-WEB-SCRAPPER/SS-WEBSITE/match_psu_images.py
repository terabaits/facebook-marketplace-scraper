import os
import re
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
DB_CONFIG = dict(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT listing_id, title, description FROM listings WHERE category='psu'")
psu_listings = {r['listing_id']: dict(r) for r in cur.fetchall()}

files = sorted(f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
print('PSU files:', len(files))
print('PSU listings:', len(psu_listings))

# Look at the first few file names
for f in files[:10]:
    print('file:', f)

# Try to find if any listing title/ID appears in any filename
matches = []
for lid, data in psu_listings.items():
    found = False
    text = ' '.join(filter(None, [lid, data.get('title', ''), data.get('description', '')])).lower()
    for f in files:
        base = os.path.splitext(f)[0].lower()
        # Check exact listing_id or words from title
        if lid.lower() in base or any(w for w in re.findall(r'[a-z0-9]+', text) if len(w) > 4 and w in base):
            matches.append((lid, f))
            found = True
            break
    if not found:
        print('no match for', lid, data.get('title'))

print('matches:', len(matches))
for m in matches[:20]:
    print(m)

cur.close(); conn.close()
