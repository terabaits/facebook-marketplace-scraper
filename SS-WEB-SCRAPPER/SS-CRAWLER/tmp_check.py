import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor()
cur.execute("SELECT source, COUNT(*) FROM listings WHERE category='gpu' AND image_url IS NOT NULL GROUP BY source")
print('gpu with image_url:', cur.fetchall())
cur.execute("SELECT source, local_image_path, image_url, listing_id FROM listings WHERE category='gpu' AND source='andelemandele' LIMIT 10")
for r in cur.fetchall(): print(r)
conn.close()
