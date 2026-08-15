import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)

print('=== MOTHERBOARDS local_image_path samples ===')
cur.execute("""
SELECT listing_id, local_image_path, image_url
FROM listings
WHERE category='motherboard' AND local_image_path IS NOT NULL AND local_image_path != ''
LIMIT 20
""")
for row in cur.fetchall():
    print(dict(row))

print('\n=== PSUs local_image_path samples ===')
cur.execute("""
SELECT listing_id, local_image_path, image_url
FROM listings
WHERE category='psu' AND local_image_path IS NOT NULL AND local_image_path != ''
LIMIT 20
""")
for row in cur.fetchall():
    print(dict(row))

print('\n=== Counts ===')
cur.execute("SELECT category, COUNT(*) as total, COUNT(local_image_path) as has_path FROM listings WHERE category IN ('motherboard','psu') GROUP BY category")
for row in cur.fetchall():
    print(dict(row))

cur.close()
conn.close()
