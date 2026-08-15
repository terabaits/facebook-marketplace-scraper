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
    
    # Check GPU model format
    cursor.execute("""
        SELECT id, model FROM gpu_reference 
        WHERE model ILIKE '%rtx%3070%'
        LIMIT 5
    """)
    print('RTX 3070 models in database:')
    for row in cursor.fetchall():
        print(f'  ID: {row[0]}, Model: "{row[1]}"')
    
    # Check other RTX formats
    cursor.execute("""
        SELECT model FROM gpu_reference 
        WHERE model ILIKE '%rtx%'
        ORDER BY model
        LIMIT 10
    """)
    print('\nFirst 10 RTX models:')
    for row in cursor.fetchall():
        print(f'  "{row[0]}"')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
