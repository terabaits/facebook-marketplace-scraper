import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor()
cur.execute("SELECT count(listing_id) FROM listings WHERE category='psu' AND local_image_path IS NOT NULL")
print('psu with local_image_path:', cur.fetchone()[0])
cur.execute("SELECT listing_id, local_image_path FROM listings WHERE category='psu' AND local_image_path IS NOT NULL LIMIT 5")
for r in cur.fetchall():
    print(r)
cur.close(); conn.close()
