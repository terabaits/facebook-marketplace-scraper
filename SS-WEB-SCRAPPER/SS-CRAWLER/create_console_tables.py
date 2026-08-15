#!/usr/bin/env python3
"""Create console database tables."""
import psycopg2

DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "ss_market"
DB_USER = "crawler"
DB_PASS = "crawler_pass"

SCHEMA_SQL = """
-- Console Reference (for game consoles like PlayStation, Xbox, Nintendo)
CREATE TABLE IF NOT EXISTS console_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(50),
    generation INTEGER,
    release_date VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Variants (different models like PS5 Slim, PS5 Pro)
CREATE TABLE IF NOT EXISTS console_variants (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,
    sku VARCHAR(100),
    storage_gb INTEGER,
    region VARCHAR(50),
    release_date VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Editions (special colors, bundles)
CREATE TABLE IF NOT EXISTS console_editions (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES console_variants(id) ON DELETE SET NULL,
    edition_name VARCHAR(200) NOT NULL,
    color VARCHAR(100),
    special_features VARCHAR(200),
    msrp_usd DECIMAL(10,2),
    msrp_eur DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Add console matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_console_id INTEGER REFERENCES console_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_variant_id INTEGER REFERENCES console_variants(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_edition_id INTEGER REFERENCES console_editions(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS console_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS console_match_method VARCHAR(50);

-- Indexes for console tables
CREATE INDEX IF NOT EXISTS idx_console_keywords ON console_reference USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_variant_keywords ON console_variants USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_edition_keywords ON console_editions USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_listings_console ON listings(matched_console_id);

SELECT 'Console tables created successfully!' AS status;
"""

def main():
    print("Connecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    try:
        with conn.cursor() as cur:
            print("Creating console tables...")
            cur.execute(SCHEMA_SQL)
            result = cur.fetchone()
            print(result[0])
        conn.commit()
        print("\nDone! Now run: python import_consoles.py")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
