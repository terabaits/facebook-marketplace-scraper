#!/usr/bin/env python3
"""Check RAM reference table structure and data"""

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
    
    # Check ram_reference table structure
    print("=== RAM Reference Table Columns ===")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'ram_reference'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['column_name']}: {col['data_type']}")
    
    # Check sample 8GB RAM entries
    print("\n=== Sample 8GB RAM Reference Entries ===")
    cursor.execute("""
        SELECT id, name, capacity_gb, speed
        FROM ram_reference
        WHERE capacity_gb = 8
        ORDER BY name
        LIMIT 20
    """)
    rows = cursor.fetchall()
    for row in rows:
        ddr_type = 'DDR4' if 'DDR4' in row['name'] else 'DDR3' if 'DDR3' in row['name'] else 'Unknown'
        print(f"  {row['id']}: {row['name']} ({row['capacity_gb']}GB, {row['speed']}) - {ddr_type}")
    
    # Check total 8GB matched listings with their RAM reference
    print("\n=== 8GB RAM Listings (matched) ===")
    cursor.execute("""
        SELECT l.listing_id, l.price_eur, l.is_active, r.name as ram_name
        FROM listings l
        JOIN ram_reference r ON l.matched_ram_id = r.id
        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
        WHERE l.category = 'ram'
            AND fl.listing_id IS NULL
            AND r.capacity_gb = 8
        ORDER BY l.price_eur
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} matched 8GB listings")
    for row in rows[:10]:
        ddr_type = 'DDR4' if 'DDR4' in (row['ram_name'] or '') else 'DDR3' if 'DDR3' in (row['ram_name'] or '') else 'Unknown'
        print(f"  {row['listing_id']}: €{row['price_eur']} - {row['ram_name'][:40]} - {ddr_type}")
    
    # Check unmatched 8GB listings
    print("\n=== 8GB RAM Listings (unmatched) ===")
    cursor.execute("""
        SELECT l.listing_id, l.title, l.price_eur, l.is_active
        FROM listings l
        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
        WHERE l.category = 'ram'
            AND fl.listing_id IS NULL
            AND l.matched_ram_id IS NULL
            AND l.title ILIKE '%8GB%'
        ORDER BY l.price_eur
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} unmatched 8GB listings")
    for row in rows[:10]:
        print(f"  {row['listing_id']}: €{row['price_eur']} - {row['title'][:50]}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
