import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check lens data
cursor.execute("""
    SELECT COUNT(*) FROM listings WHERE category = 'lens'
""")
print(f"Total lens listings: {cursor.fetchone()[0]}")

cursor.execute("""
    SELECT COUNT(*) FROM listings WHERE category = 'lens' AND matched_lens_id IS NOT NULL
""")
print(f"Matched lens listings: {cursor.fetchone()[0]}")

cursor.execute("""
    SELECT COUNT(*) FROM lens_reference
""")
print(f"Total lens reference models: {cursor.fetchone()[0]}")

cursor.execute("""
    SELECT DISTINCT brand FROM lens_reference ORDER BY brand LIMIT 10
""")
print(f"\nLens brands: {[row[0] for row in cursor.fetchall()]}")

cursor.close()
conn.close()
