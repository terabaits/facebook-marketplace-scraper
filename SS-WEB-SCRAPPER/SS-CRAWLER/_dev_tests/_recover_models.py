import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
# Find listings for the 14 empty-model reference rows
cur.execute("""
    SELECT lr.id, lr.brand, lr.model_number, ll.model, ll.title, COUNT(*) as cnt
    FROM laptop_reference lr
    JOIN laptop_listings ll ON ll.laptop_reference_id = lr.id
    WHERE lr.model = 'Unknown' AND lr.brand NOT IN ('Cits', '(unknown)')
    GROUP BY lr.id, lr.brand, lr.model_number, ll.model, ll.title
    ORDER BY lr.id, cnt DESC
""")
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]:<11} lr_mn={r[2]!r:<22} ll_model={r[3]!r:<30} title={r[4]!r}')
