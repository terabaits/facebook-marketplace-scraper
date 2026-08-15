import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("SELECT id, listing_id, title FROM laptop_listings WHERE laptop_reference_id = 670")
for r in cur.fetchall(): print(r)
cur.execute("SELECT COUNT(*) FROM laptop_listings WHERE laptop_reference_id = 670")
print('Count:', cur.fetchone()[0])
