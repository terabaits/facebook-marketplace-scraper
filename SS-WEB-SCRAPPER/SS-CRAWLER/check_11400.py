import sys
sys.path.insert(0, 'src')
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Check i5-11400 variants
print("Intel Core i5-11400 variants:")
cur.execute("""
    SELECT id, cpu_name, processor_number, socket 
    FROM cpu_reference 
    WHERE cpu_name ILIKE '%i5-11400%'
    ORDER BY cpu_name
""")
for row in cur.fetchall():
    print(f"  ID {row[0]}: {row[1]}")
    print(f"    Processor number: {row[2]}")
    print(f"    Socket: {row[3]}")

cur.close()
conn.close()
