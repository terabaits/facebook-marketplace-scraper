import sys
sys.path.insert(0, 'src')
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Check H510M motherboards
print("Gigabyte H510M motherboards:")
cur.execute("""
    SELECT id, brand, model, chipset, socket 
    FROM motherboard_reference 
    WHERE model ILIKE '%h510m%'
    ORDER BY id
""")
for row in cur.fetchall():
    print(f"  ID {row[0]}: {row[1]} {row[2]}")
    print(f"    Chipset: {row[3]}, Socket: {row[4]}")

print("\nMotherboard ID 6550:")
cur.execute("""
    SELECT id, brand, model, chipset, socket 
    FROM motherboard_reference 
    WHERE id = 6550
""")
for row in cur.fetchall():
    print(f"  ID {row[0]}: {row[1]} {row[2]}")
    print(f"    Chipset: {row[3]}, Socket: {row[4]}")

cur.close()
conn.close()
