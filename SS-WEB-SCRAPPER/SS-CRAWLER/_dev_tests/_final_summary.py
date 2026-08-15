import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()

print('='*60)
print('LAPTOP_REFERENCE NORMALIZATION — FINAL STATE')
print('='*60)

cur.execute('SELECT COUNT(*) FROM laptop_reference')
total = cur.fetchone()[0]
print(f'Total rows: {total}')

cur.execute('SELECT COUNT(*) FROM laptop_reference WHERE model_number IS NOT NULL')
with_num = cur.fetchone()[0]
print(f'With model_number: {with_num} ({100*with_num/total:.0f}%)')

cur.execute("SELECT COUNT(*) FROM laptop_reference WHERE model = 'Unknown'")
unknown = cur.fetchone()[0]
print(f'Marked Unknown (noise): {unknown}')

cur.execute('SELECT COUNT(*) FROM laptop_reference WHERE model_number IS NULL AND model IS NOT NULL AND model <> %s', ('Unknown',))
generic = cur.fetchone()[0]
print(f'Generic (no separate SKU): {generic}')

cur.execute('SELECT COUNT(*) FROM laptop_reference WHERE model IS NULL')
no_model = cur.fetchone()[0]
print(f'NULL model: {no_model}')

print()
print('--- Per-brand breakdown ---')
cur.execute("""
    SELECT brand,
           COUNT(*) as total,
           SUM(CASE WHEN model_number IS NOT NULL THEN 1 ELSE 0 END) as with_num,
           SUM(CASE WHEN model = 'Unknown' THEN 1 ELSE 0 END) as unknown
    FROM laptop_reference
    GROUP BY brand
    ORDER BY total DESC
""")
print(f'{"Brand":<14} {"Total":>6} {"WithNum":>8} {"Unknown":>8}')
for r in cur.fetchall():
    print(f'{r[0]:<14} {r[1]:>6} {r[2]:>8} {r[3]:>8}')

print()
print('--- Sample of successfully normalized rows ---')
cur.execute("""
    SELECT id, brand, model, model_number, display_size
    FROM laptop_reference
    WHERE model_number IS NOT NULL AND model <> 'Unknown'
    ORDER BY RANDOM() LIMIT 15
""")
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]:<11} {r[2]:<22} {r[3]!s:<14} {r[4]}')
