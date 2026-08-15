-- Listing Versioning Schema
-- Handles cases where ss.com reuses listing IDs for different listings

-- Add version column to main listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_listing_id_key;
ALTER TABLE listings ADD CONSTRAINT listings_listing_id_version_unique UNIQUE (listing_id, version_number);

-- Add version column to computer_listings table  
ALTER TABLE computer_listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE computer_listings DROP CONSTRAINT IF EXISTS computer_listings_listing_id_key;
ALTER TABLE computer_listings ADD CONSTRAINT computer_listings_listing_id_version_unique UNIQUE (listing_id, version_number);

-- Create function to generate versioned listing ID
CREATE OR REPLACE FUNCTION generate_versioned_listing_id(
    p_listing_id VARCHAR(50),
    p_version INTEGER
) RETURNS VARCHAR(50) AS $$
BEGIN
    IF p_version <= 1 THEN
        RETURN p_listing_id;
    ELSE
        RETURN p_listing_id || '_v' || p_version;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to get next version number for a listing
CREATE OR REPLACE FUNCTION get_next_listing_version(
    p_listing_id VARCHAR(50),
    p_table_name VARCHAR(50) DEFAULT 'listings'
) RETURNS INTEGER AS $$
DECLARE
    v_max_version INTEGER;
BEGIN
    IF p_table_name = 'listings' THEN
        SELECT COALESCE(MAX(version_number), 0) + 1
        INTO v_max_version
        FROM listings
        WHERE listing_id = p_listing_id;
    ELSIF p_table_name = 'computer_listings' THEN
        SELECT COALESCE(MAX(version_number), 0) + 1
        INTO v_max_version
        FROM computer_listings
        WHERE listing_id = p_listing_id;
    ELSE
        RAISE EXCEPTION 'Unknown table: %', p_table_name;
    END IF;
    
    RETURN v_max_version;
END;
$$ LANGUAGE plpgsql;

-- Create index for version lookups
CREATE INDEX IF NOT EXISTS idx_listings_version ON listings(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_computer_listings_version ON computer_listings(listing_id, version_number);

-- Update existing listing_versions table to reference versioned IDs properly
-- (Keep existing structure, just ensure it works with new versioned IDs)

-- Add content fingerprint column for quick comparison
ALTER TABLE listings ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);
ALTER TABLE computer_listings ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_listings_fingerprint ON listings(content_fingerprint);
CREATE INDEX IF NOT EXISTS idx_computer_listings_fingerprint ON computer_listings(content_fingerprint);
