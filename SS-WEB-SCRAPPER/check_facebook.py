import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

print('=== Facebook Listings ===')
cursor.execute("SELECT listing_id, title, source, category, image_url, local_image_path FROM listings WHERE listing_id LIKE 'fb_%%' LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f'ID: {row[0]}')
    print(f'  Title: {row[1][:50] if row[1] else "None"}')
    print(f'  Source: {row[2]}')
    print(f'  Category: {row[3]}')
    print(f'  Image URL: {row[4][:60] if row[4] else "None"}')
    print(f'  Local Image: {row[5]}')
    print()

print('=== Source Distribution ===')
cursor.execute('SELECT source, COUNT(*) FROM listings GROUP BY source ORDER BY COUNT(*) DESC')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

cursor.close()
conn.close()
