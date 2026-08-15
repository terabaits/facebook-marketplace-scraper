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
    
    # Check columns in listings table
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'listings'
        ORDER BY ordinal_position
    """)
    print('Columns in listings table:')
    for row in cursor.fetchall():
        print(f'  {row[0]}')
    
    # Check if RTX 3070 exists
    cursor.execute("""
        SELECT id, model FROM gpu_reference 
        WHERE model ILIKE '%3070%'
        LIMIT 5
    """)
    print('\nRTX 3070 in database:')
    for row in cursor.fetchall():
        print(f'  ID: {row[0]}, Model: {row[1]}')
    
    # Check sold listings for RTX 3070
    cursor.execute("""
        SELECT price_eur, is_sold, date_posted
        FROM listings 
        WHERE matched_gpu_id IN (SELECT id FROM gpu_reference WHERE model ILIKE '%3070%')
        AND price_eur > 0
        LIMIT 5
    """)
    print('\nSold RTX 3070 listings:')
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f'  Price: €{row[0]}, Sold: {row[1]}, Date: {row[2]}')
    else:
        print('  No listings found')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
