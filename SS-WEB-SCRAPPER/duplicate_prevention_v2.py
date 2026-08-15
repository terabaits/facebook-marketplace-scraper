#!/usr/bin/env python3
"""
SS-Crawler Duplicate Prevention v2
Checks title + description + location to identify same listing.
Handles price changes as updates, new descriptions as new versions.
"""

import psycopg2
import hashlib
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def normalize_text(text):
    """Normalize text for comparison."""
    if not text:
        return ""
    # Remove extra whitespace, lowercase
    return ' '.join(str(text).lower().split())


def content_hash(title, description):
    """Create hash of normalized title+description for quick comparison."""
    combined = normalize_text(title) + "|" + normalize_text(description)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def upsert_listing_v2(listing_data):
    """
    Smart upsert that:
    1. Checks for existing listing by listing_id first
    2. If listing_id exists but description changed → new version
    3. If same title+description+location exists → update (including price)
    4. Otherwise insert new
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    new_hash = content_hash(
        listing_data.get('title'),
        listing_data.get('description')
    )
    
    # Step 1: Check by listing_id (exact match)
    cursor.execute("""
        SELECT id, content_hash, price_eur, is_active
        FROM listings 
        WHERE listing_id = %s
        ORDER BY date_posted DESC
        LIMIT 1
    """, (listing_data.get('listing_id'),))
    
    existing_by_id = cursor.fetchone()
    
    if existing_by_id:
        db_id, old_hash, old_price, was_active = existing_by_id
        
        if old_hash != new_hash:
            # Same listing_id but different content = new version
            # Keep old version but mark inactive
            cursor.execute("""
                UPDATE listings SET is_active = false
                WHERE id = %s
            """, (db_id,))
            print(f"Content changed for {listing_data.get('listing_id')} - creating new version")
            # Fall through to insert new
        else:
            # Same content, just update metadata
            cursor.execute("""
                UPDATE listings 
                SET 
                    last_seen_at = NOW(),
                    is_active = true,
                    listing_url = %s,
                    price_eur = %s,
                    price_changes = CASE 
                        WHEN price_eur != %s AND price_eur IS NOT NULL THEN 
                            COALESCE(price_changes, '[]'::jsonb) || 
                            jsonb_build_object(
                                'old_price', price_eur,
                                'new_price', %s,
                                'changed_at', NOW()
                            )
                        ELSE price_changes
                    END
                WHERE id = %s
            """, (
                listing_data.get('listing_url'),
                listing_data.get('price_eur'),
                listing_data.get('price_eur'),
                listing_data.get('price_eur'),
                db_id
            ))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"Updated existing listing {db_id}")
            return db_id
    
    # Step 2: Check by title + description + location (same content, different ID)
    cursor.execute("""
        SELECT id, listing_id, price_eur
        FROM listings 
        WHERE content_hash = %s
          AND seller_location = %s
          AND category = %s
          AND is_active = true
        ORDER BY date_posted DESC
        LIMIT 1
    """, (
        new_hash,
        listing_data.get('seller_location'),
        listing_data.get('category')
    ))
    
    existing_by_content = cursor.fetchone()
    
    if existing_by_content:
        # Same content found, update with new ID and price
        db_id, old_listing_id, old_price = existing_by_content
        
        cursor.execute("""
            UPDATE listings 
            SET 
                listing_id = %s,
                listing_url = %s,
                last_seen_at = NOW(),
                price_eur = %s,
                is_active = true,
                price_changes = CASE 
                    WHEN price_eur != %s THEN 
                        COALESCE(price_changes, '[]'::jsonb) || 
                        jsonb_build_object(
                            'old_price', price_eur,
                            'new_price', %s,
                            'changed_at', NOW()
                        )
                    ELSE price_changes
                END
            WHERE id = %s
        """, (
            listing_data.get('listing_id'),
            listing_data.get('listing_url'),
            listing_data.get('price_eur'),
            listing_data.get('price_eur'),
            listing_data.get('price_eur'),
            db_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Updated listing {db_id} (was {old_listing_id}, now {listing_data.get('listing_id')})")
        return db_id
    
    # Step 3: Insert new listing
    cursor.execute("""
        INSERT INTO listings 
        (listing_id, category, title, description, content_hash, price_eur, 
         seller_name, seller_location, seller_phone, seller_email,
         date_posted, listing_url, first_seen_at, last_seen_at, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), true)
        RETURNING id
    """, (
        listing_data.get('listing_id'),
        listing_data.get('category'),
        listing_data.get('title'),
        listing_data.get('description'),
        new_hash,
        listing_data.get('price_eur'),
        listing_data.get('seller_name'),
        listing_data.get('seller_location'),
        listing_data.get('seller_phone'),
        listing_data.get('seller_email'),
        listing_data.get('date_posted'),
        listing_data.get('listing_url')
    ))
    
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Inserted new listing {new_id}")
    return new_id


# Database migration - add content_hash column
def add_content_hash_column():
    """Add content_hash column for efficient duplicate detection."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        ALTER TABLE listings 
        ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16),
        ADD COLUMN IF NOT EXISTS price_changes JSONB DEFAULT '[]'::jsonb
    """)
    
    # Create index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_listings_content_hash 
        ON listings(content_hash) 
        WHERE is_active = true
    """)
    
    # Populate hash for existing rows
    cursor.execute("""
        UPDATE listings 
        SET content_hash = MD5(
            LOWER(REGEXP_REPLACE(title, '\s+', ' ', 'g')) || 
            '|' || 
            LOWER(REGEXP_REPLACE(description, '\s+', ' ', 'g'))
        )::varchar(16)
        WHERE content_hash IS NULL
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Added content_hash column and populated existing data")


if __name__ == '__main__':
    add_content_hash_column()
    
    # Test
    test_listing = {
        'listing_id': 'test_v123',
        'category': 'cpu',
        'title': 'AMD Ryzen 5 7600',
        'description': 'Lietots procesors, darba stāvoklī',
        'price_eur': 115.00,
        'seller_name': 'Test Seller',
        'seller_location': 'Riga',
        'seller_phone': '12345678',
        'seller_email': None,
        'date_posted': datetime.now(),
        'listing_url': 'https://ss.lv/test_v123'
    }
    upsert_listing_v2(test_listing)
