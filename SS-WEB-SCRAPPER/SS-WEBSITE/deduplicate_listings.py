#!/usr/bin/env python3
"""
Deduplicate listings by keeping only the most recent entry
for each unique title+price+location combination.
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def deduplicate():
    """Remove duplicate listings, keeping only the most recent."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 70)
    print("DEDUPLICATING LISTINGS")
    print("=" * 70)
    
    # Find duplicates
    cursor.execute('''
        SELECT title, price_eur, seller_location, COUNT(*) as cnt,
               MAX(id) as keep_id,
               ARRAY_AGG(id) as all_ids
        FROM listings
        WHERE is_active = true
        GROUP BY title, price_eur, seller_location
        HAVING COUNT(*) > 1
    ''')
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicates found!")
        return
    
    print(f"Found {len(duplicates)} duplicate groups")
    
    # Mark older duplicates as inactive
    total_removed = 0
    for row in duplicates:
        title, price, location, cnt, keep_id, all_ids = row
        ids_to_remove = [id for id in all_ids if id != keep_id]
        
        cursor.execute('''
            UPDATE listings 
            SET is_active = false 
            WHERE id = ANY(%s)
        ''', (ids_to_remove,))
        
        total_removed += len(ids_to_remove)
    
    conn.commit()
    
    print(f"Marked {total_removed} duplicate listings as inactive")
    
    # Verify
    cursor.execute('''
        SELECT COUNT(*) 
        FROM listings 
        WHERE is_active = true
    ''')
    active_count = cursor.fetchone()[0]
    print(f"Active listings after cleanup: {active_count}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Deduplication complete!")
    print("Old duplicates marked inactive (not deleted, preserved for history)")


if __name__ == '__main__':
    deduplicate()
