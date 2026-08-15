import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check ALL columns in lens_reference for a match
print("=== Checking all columns ===")
cursor.execute("""
    SELECT * FROM lens_reference 
    LIMIT 1
""")
col_names = [desc[0] for desc in cursor.description]
row = cursor.fetchone()
print("Columns:", col_names)
print("\nFirst row:")
for i, col in enumerate(col_names):
    print(f"  {col}: {row[i]}")

# Check if the ID format is consistent
print("\n=== Unique ID patterns ===")
cursor.execute("""
    SELECT id::varchar FROM lens_reference 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
