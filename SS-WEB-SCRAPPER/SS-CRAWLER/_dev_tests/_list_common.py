"""List the most common (brand, model, model_number, display_size) tuples
that still have NULL material/USB — to prioritize web searches."""
import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("""
    SELECT lr.brand, lr.model, lr.model_number, lr.display_size,
           COUNT(*) as listings
    FROM laptop_reference lr
    JOIN laptop_listings ll ON ll.laptop_reference_id = lr.id
    WHERE lr.material IS NULL AND lr.usb_count IS NULL
      AND lr.model IS NOT NULL AND lr.model <> 'Unknown'
    GROUP BY lr.brand, lr.model, lr.model_number, lr.display_size
    ORDER BY listings DESC
    LIMIT 60
""")
print("Top 60 products needing specs (by listing count):")
for r in cur.fetchall():
    print(f'  {r[0]:<11} {r[1]:<22} {r[2] or "":<14} {r[3] or "":<5} listings={r[4]}')
