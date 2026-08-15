-- Database schema updates for SS-WEBSITE fixes
-- Run this against your PostgreSQL database

-- 1. Add content_hash column for duplicate prevention
ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16),
ADD COLUMN IF NOT EXISTS price_changes JSONB DEFAULT '[]'::jsonb;

-- Create index for fast duplicate detection
CREATE INDEX IF NOT EXISTS idx_listings_content_hash 
ON listings(content_hash) 
WHERE is_active = true;

-- Populate content_hash for existing rows
UPDATE listings 
SET content_hash = MD5(
    COALESCE(LOWER(REGEXP_REPLACE(title, '\s+', ' ', 'g')), '') || 
    '|' || 
    COALESCE(LOWER(REGEXP_REPLACE(description, '\s+', ' ', 'g')), '')
)::varchar(16)
WHERE content_hash IS NULL;

-- 2. Create flagged_listings table for global flagging
CREATE TABLE IF NOT EXISTS flagged_listings (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50),
    comment TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_flagged_listings_category ON flagged_listings(category) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_flagged_listings_active ON flagged_listings(listing_id) WHERE is_active = TRUE;

-- Verify
SELECT 'content_hash column added' as status;
SELECT COUNT(*) as rows_with_hash FROM listings WHERE content_hash IS NOT NULL;
SELECT COUNT(*) as flagged_table_exists FROM information_schema.tables WHERE table_name = 'flagged_listings';
