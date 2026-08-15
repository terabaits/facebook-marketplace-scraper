-- Create flagged_listings table for global flagging (all categories)
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

-- Migrate console_flagged_listings if exists
INSERT INTO flagged_listings (listing_id, category, comment, flagged_at, is_active)
SELECT listing_id, 'console', reason, flagged_at, is_active
FROM flagged_listings_old
ON CONFLICT (listing_id) DO NOTHING;

-- Verify
SELECT COUNT(*) as total_flagged FROM flagged_listings WHERE is_active = TRUE;
