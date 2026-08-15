import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("""SELECT id, brand, model, display_size FROM laptop_reference
WHERE model_number IS NULL AND model IS NOT NULL
ORDER BY brand, model""")
rows=cur.fetchall()
print(f'Remaining {len(rows)} unresolved:')
for r in rows: print(r)
