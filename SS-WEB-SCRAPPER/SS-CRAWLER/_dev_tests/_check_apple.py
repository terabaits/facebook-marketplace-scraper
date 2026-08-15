import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("SELECT id, brand, model, model_number FROM laptop_reference WHERE brand='Apple' ORDER BY id LIMIT 15")
for r in cur.fetchall(): print(r)
