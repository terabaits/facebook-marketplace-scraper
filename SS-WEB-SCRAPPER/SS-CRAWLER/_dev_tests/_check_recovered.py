import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
# Look at the 33 recovered rows
cur.execute("""
    SELECT id, brand, model, model_number, display_size
    FROM laptop_reference
    WHERE id IN (150, 183, 200, 211, 276, 281, 310, 340, 361, 404, 424, 491, 586, 630, 431, 510, 192)
    ORDER BY id
""")
print("=== Recovered rows ===")
for r in cur.fetchall(): print(f'  [{r[0]}] {r[1]:<12} {r[2]!r:<25} {r[3]!r:<20} {r[4]}')
