"""Final report on laptop_reference normalization progress."""
import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()

print('='*70)
print('LAPTOP_REFERENCE NORMALIZATION — FINAL REPORT')
print('='*70)

cur.execute('SELECT COUNT(*) FROM laptop_reference')
total = cur.fetchone()[0]
print(f'Total rows: {total}')

cur.execute('SELECT COUNT(*) FROM laptop_reference WHERE model_number IS NOT NULL')
with_num = cur.fetchone()[0]
print(f'With model_number (real SKUs): {with_num} ({100*with_num/total:.1f}%)')

cur.execute("SELECT COUNT(*) FROM laptop_reference WHERE model = 'Unknown'")
unknown = cur.fetchone()[0]
print(f'Marked Unknown (noise): {unknown}')

cur.execute("SELECT COUNT(*) FROM laptop_reference WHERE model IS NOT NULL AND model <> 'Unknown' AND model_number IS NULL")
generic = cur.fetchone()[0]
print(f'Generic (no separate SKU needed): {generic}')

print()
print('--- Brand breakdown ---')
cur.execute("""
    SELECT brand,
           COUNT(*) as total,
           SUM(CASE WHEN model_number IS NOT NULL THEN 1 ELSE 0 END) as with_num,
           SUM(CASE WHEN model = 'Unknown' THEN 1 ELSE 0 END) as unknown
    FROM laptop_reference
    GROUP BY brand
    ORDER BY total DESC
""")
print(f'{"Brand":<14} {"Total":>6} {"WithNum":>8} {"Unknown":>8} {"%Coverage":>10}')
for r in cur.fetchall():
    coverage = 100 * r[2] / r[1] if r[1] else 0
    print(f'{r[0]:<14} {r[1]:>6} {r[2]:>8} {r[3]:>8} {coverage:>9.0f}%')

print()
print('--- All real-SKU rows (model_number set) ---')
cur.execute("""
    SELECT id, brand, model, model_number, display_size
    FROM laptop_reference
    WHERE model_number IS NOT NULL
    ORDER BY brand, model, model_number
""")
rows = cur.fetchall()
print(f'Total: {len(rows)}')
for r in rows:
    print(f'  [{r[0]:3}] {r[1]:<11} {r[2]:<22} {r[3]!s:<14} {r[4]}')
