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
    
    # Test the extension query
    normalized = 'geforce rtx 3070'
    print(f"Testing query with: '{normalized}'")
    
    cursor.execute("""
        SELECT id, model FROM gpu_reference 
        WHERE model ILIKE %s
        AND model NOT ILIKE '%%ti%%'
        AND model NOT ILIKE '%%super%%'
        LIMIT 1
    """, (f'%{normalized}%',))
    
    result = cursor.fetchone()
    print(f"Query result: {result}")
    
    # Also try simpler query
    cursor.execute("""
        SELECT id, model FROM gpu_reference 
        WHERE model ILIKE '%%rtx%%3070%%'
        AND model NOT ILIKE '%%ti%%'
        LIMIT 1
    """)
    
    result2 = cursor.fetchone()
    print(f"Simple query result: {result2}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
