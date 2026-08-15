import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, database='ss_market', user='crawler', password='crawler_pass')
cursor = conn.cursor()

# Check Facebook GPU listings - do they have matched_gpu_id?
print("=== Facebook GPU listings details ===")
cursor.execute("""
    SELECT listing_id, title, price_eur, matched_gpu_id, confidence_score, match_method
    FROM listings 
    WHERE category = 'gpu' AND source = 'facebook_extension'
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  Title: {row[1][:60]}")
    print(f"  Price: €{row[2]}")
    print(f"  matched_gpu_id: {row[3]}")
    print(f"  confidence_score: {row[4]}")
    print(f"  match_method: {row[5]}")
    print("---")

# Compare with ss.com listings
print("\n=== SS.com GPU listings (for comparison) ===")
cursor.execute("""
    SELECT listing_id, title, price_eur, matched_gpu_id, confidence_score, match_method
    FROM listings 
    WHERE category = 'gpu' AND source = 'ss.com' AND matched_gpu_id IS NOT NULL
    LIMIT 3
""")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  Title: {row[1][:60]}")
    print(f"  matched_gpu_id: {row[3]}")
    print(f"  confidence_score: {row[4]}")
    print("---")

cursor.close()
conn.close()
