import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cur = conn.cursor()
cur.execute("SELECT listing_id, local_image_path FROM listings WHERE category='psu' AND local_image_path IS NOT NULL")
print(cur.fetchall())
conn.close()
