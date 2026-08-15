import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        database='ss_market',
        user='crawler',
        password='crawler_pass'
    )
    cursor = conn.cursor()
    
    # Check console listings
    cursor.execute("SELECT COUNT(*) FROM listings WHERE category='console'")
    count = cursor.fetchone()[0]
    print(f'Console listings: {count}')
    
    # Show all categories
    cursor.execute("SELECT category, COUNT(*) FROM listings GROUP BY category ORDER BY category")
    print('\nAll categories:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
