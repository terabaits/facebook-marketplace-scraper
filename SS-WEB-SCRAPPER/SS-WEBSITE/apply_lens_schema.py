#!/usr/bin/env python3
"""Apply lens schema to database."""

import psycopg2
import os

DB_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 5433)),
    'database': os.environ.get('DATABASE_NAME', 'ss_market'),
    'user': os.environ.get('DATABASE_USER', 'crawler'),
    'password': os.environ.get('DATABASE_PASSWORD', 'crawler_pass')
}

LENS_SCHEMA = """
-- Add lens matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_lens_id VARCHAR(100);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS lens_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS lens_match_method VARCHAR(50);

-- Create index for lens matching
CREATE INDEX IF NOT EXISTS idx_listings_lens ON listings(matched_lens_id);
CREATE INDEX IF NOT EXISTS idx_listings_lens_confidence ON listings(lens_confidence_score);
"""

def apply_schema():
    """Apply lens schema to database."""
    print(f"Connecting to database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Applying lens schema...")
        cursor.execute(LENS_SCHEMA)
        conn.commit()
        
        # Verify columns were added
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'listings' 
            AND column_name LIKE '%lens%'
        """)
        
        columns = cursor.fetchall()
        print(f"\nLens-related columns in 'listings' table:")
        for col in columns:
            print(f"  - {col[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Lens schema applied successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error applying schema: {e}")
        return False

if __name__ == "__main__":
    apply_schema()
