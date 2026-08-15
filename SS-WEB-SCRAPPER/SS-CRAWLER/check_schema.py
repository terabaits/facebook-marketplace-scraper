#!/usr/bin/env python
import psycopg2

try:
    conn = psycopg2.connect("dbname=scrapedata user=postgres password=yourpassword host=localhost")
    cursor = conn.cursor()
    
    # Get computer_listings columns
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'computer_listings' 
        ORDER BY ordinal_position;
    """)
    columns = [row[0] for row in cursor.fetchall()]
    print("computer_listings columns:", columns)
    
    # Get some sample data
    cursor.execute("""
        SELECT listing_id, title, matched_ram_id, ram_match_method 
        FROM computer_listings 
        WHERE is_active = true 
        ORDER BY last_seen_at DESC 
        LIMIT 5;
    """)
    print("\nSample listings:")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
