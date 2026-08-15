#!/usr/bin/env python3
"""Check RAM reference type column"""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check distinct type values
    print("=== RAM Reference Distinct Types ===")
    cursor.execute("""
        SELECT DISTINCT type, COUNT(*) as count
        FROM ram_reference
        GROUP BY type
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"  {row['type']}: {row['count']} entries")
    
    # Check 8GB RAM by DDR type using speed column
    print("\n=== 8GB RAM by DDR Type (from speed column) ===")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN speed LIKE 'DDR4%' THEN 'DDR4'
                WHEN speed LIKE 'DDR3%' THEN 'DDR3'
                ELSE 'Unknown'
            END as ddr_type,
            COUNT(*) as count
        FROM ram_reference
        WHERE capacity_gb = 8
        GROUP BY ddr_type
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"  {row['ddr_type']}: {row['count']} entries")
    
    # Get DDR4 8GB matched listings
    print("\n=== DDR4 8GB RAM Listings (matched) ===")
    cursor.execute("""
        SELECT l.listing_id, l.price_eur, r.name as ram_name, r.speed
        FROM listings l
        JOIN ram_reference r ON l.matched_ram_id = r.id
        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
        WHERE l.category = 'ram'
            AND fl.listing_id IS NULL
            AND r.capacity_gb = 8
            AND r.speed LIKE 'DDR4%'
        ORDER BY l.price_eur
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} DDR4 8GB matched listings")
    for row in rows:
        print(f"  {row['listing_id']}: {row['price_eur']} - {row['ram_name'][:40]} - {row['speed']}")
    
    # Get DDR3 8GB matched listings
    print("\n=== DDR3 8GB RAM Listings (matched) ===")
    cursor.execute("""
        SELECT l.listing_id, l.price_eur, r.name as ram_name, r.speed
        FROM listings l
        JOIN ram_reference r ON l.matched_ram_id = r.id
        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
        WHERE l.category = 'ram'
            AND fl.listing_id IS NULL
            AND r.capacity_gb = 8
            AND r.speed LIKE 'DDR3%'
        ORDER BY l.price_eur
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} DDR3 8GB matched listings")
    for row in rows[:10]:
        print(f"  {row['listing_id']}: {row['price_eur']} - {row['ram_name'][:40]} - {row['speed']}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
