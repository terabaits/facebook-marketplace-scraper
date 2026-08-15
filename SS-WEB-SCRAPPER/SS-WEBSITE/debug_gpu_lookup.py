import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check what the extension is searching for
normalized = "GeForce GTX 1080 Ti"
search_pattern = f"%{normalized}%"

print(f"=== Searching for: '{search_pattern}' ===")

# Try the exact query from extension_api.py
cursor.execute("""
    SELECT id, model FROM gpu_reference 
    WHERE model ILIKE %s
    LIMIT 1
""", (search_pattern,))

result = cursor.fetchone()
print(f"Result: {result}")

# Let's see what GTX 1080 models exist
print("\n=== All GTX 1080 models in database ===")
cursor.execute("""
    SELECT id, model FROM gpu_reference 
    WHERE model ILIKE '%gtx%1080%'
    ORDER BY model
""")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]}")

# Try with just "1080 Ti"
print("\n=== Searching for '%1080 ti%' ===")
cursor.execute("""
    SELECT id, model FROM gpu_reference 
    WHERE model ILIKE '%1080 ti%'
    LIMIT 1
""", ())
result = cursor.fetchone()
print(f"Result: {result}")

cursor.close()
conn.close()
