#!/usr/bin/env python3
"""
SS-Crawler Duplicate Prevention Patch
Add this logic to your listing repository before inserting new listings.
"""

import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def upsert_listing(listing_data):
    """
    Insert or update listing based on content, not just listing_id.
    Call this instead of insert() in your crawler.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check for existing listing with same title + price + location
    cursor.execute("""
        SELECT id, listing_id, is_active 
        FROM listings 
        WHERE title = %s 
          AND price_eur = %s 
          AND seller_location = %s
          AND category = %s
        ORDER BY date_posted DESC
        LIMIT 1
    """, (
        listing_data.get('title'),
        listing_data.get('price_eur'),
        listing_data.get('seller_location'),
        listing_data.get('category')
    ))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing listing
        db_id, old_listing_id, was_active = existing
        
        cursor.execute("""
            UPDATE listings 
            SET 
                listing_id = %s,
                listing_url = %s,
                is_active = true,
                last_seen_at = NOW(),
                price_changes = CASE 
                    WHEN price_eur != %s THEN 
                        COALESCE(price_changes, '[]'::jsonb) || 
                        jsonb_build_object(
                            'old_price', price_eur,
                            'new_price', %s,
                            'changed_at', NOW()
                        )
                    ELSE price_changes
                END,
                price_eur = %s,
                title = %s,
                description = %s
            WHERE id = %s
        """, (
            listing_data.get('listing_id'),
            listing_data.get('listing_url'),
            listing_data.get('price_eur'),
            listing_data.get('price_eur'),
            listing_data.get('price_eur'),
            listing_data.get('title'),
            listing_data.get('description'),
            db_id
        ))
        
        print(f"Updated existing listing {db_id} (was {old_listing_id}, now {listing_data.get('listing_id')})")
        conn.commit()
        cursor.close()
        conn.close()
        return db_id
    else:
        # Insert new listing
        cursor.execute("""
            INSERT INTO listings 
            (listing_id, category, title, description, price_eur, 
             seller_name, seller_location, seller_phone, seller_email,
             date_posted, listing_url, first_seen_at, last_seen_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), true)
            RETURNING id
        """, (
            listing_data.get('listing_id'),
            listing_data.get('category'),
            listing_data.get('title'),
            listing_data.get('description'),
            listing_data.get('price_eur'),
            listing_data.get('seller_name'),
            listing_data.get('seller_location'),
            listing_data.get('seller_phone'),
            listing_data.get('seller_email'),
            listing_data.get('date_posted'),
            listing_data.get('listing_url')
        ))
        
        new_id = cursor.fetchone()[0]
        print(f"Inserted new listing {new_id}")
        conn.commit()
        cursor.close()
        conn.close()
        return new_id


# Example usage
if __name__ == '__main__':
    test_listing = {
        'listing_id': 'test_v2',
        'category': 'cpu',
        'title': 'Test AMD Ryzen CPU',
        'description': 'Test description',
        'price_eur': 110.00,
        'seller_name': 'Test Seller',
        'seller_location': 'Riga',
        'seller_phone': '12345678',
        'seller_email': None,
        'date_posted': datetime.now(),
        'listing_url': 'https://ss.lv/test'
    }
    upsert_listing(test_listing)
