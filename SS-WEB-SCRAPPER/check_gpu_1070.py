import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cursor = conn.cursor()

print("Searching for 1070 GPUs:")
cursor.execute("SELECT id, model FROM gpu_reference WHERE model ILIKE '%1070%' LIMIT 10")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Model: {row[1]}")

print("\nSearching for GTX patterns:")
cursor.execute("SELECT id, model FROM gpu_reference WHERE model ILIKE '%gtx%' LIMIT 20")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Model: {row[1]}")

conn.close()
