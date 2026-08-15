import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("SELECT id, brand, model, model_number, display_size, material, usb_count FROM laptop_reference WHERE brand = 'TestBrand'")
for r in cur.fetchall(): print(r)
