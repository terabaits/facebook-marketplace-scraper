import os, psycopg2
from psycopg2.extras import RealDictCursor

folder = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/motherboards'
files = set(os.listdir(folder))

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT listing_id, local_image_path, image_url FROM listings WHERE category='motherboard'")
rows = cur.fetchall()
cur.close(); conn.close()

missing_path = []
missing_file = []
has_image = []
for row in rows:
    path = row['local_image_path']
    if not path:
        missing_path.append(row['listing_id'])
    else:
        fn = os.path.basename(path)
        if fn not in files:
            missing_file.append((row['listing_id'], path))
        else:
            has_image.append((row['listing_id'], path))

print(f'Total motherboard listings: {len(rows)}')
print(f'Has local_image_path: {len(rows)-len(missing_path)}')
print(f'Missing local_image_path: {missing_path}')
print(f'Path set but file missing on disk: {len(missing_file)}')
for lid, path in missing_file[:10]:
    print(' ', lid, path)
print(f'Renderable images: {len(has_image)}')
