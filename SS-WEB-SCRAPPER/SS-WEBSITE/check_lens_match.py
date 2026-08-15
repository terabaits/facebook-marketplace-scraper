import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check if matched_lens_id matches any column in lens_reference
cursor.execute("""
    SELECT lens_name FROM lens_reference 
    WHERE lens_name LIKE '%Canon_10-18%'
    LIMIT 5
""")
print("Matching lens_name:")
for row in cursor.fetchall():
    print(f"  {row}")

# Check normalized_name
cursor.execute("""
    SELECT normalized_name FROM lens_reference 
    WHERE normalized_name LIKE '%canon%10%18%'
    LIMIT 5
""")
print("\nMatching normalized_name:")
for row in cursor.fetchall():
    print(f"  {row}")

cursor.close()
conn.close()
