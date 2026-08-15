import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'laptop_reference'::regclass")
for r in cur.fetchall(): print(r[0], '|', r[1])

cur.execute("SELECT DISTINCT material FROM laptop_reference WHERE material IS NOT NULL")
print("\nExisting material values:", [r[0] for r in cur.fetchall()])
