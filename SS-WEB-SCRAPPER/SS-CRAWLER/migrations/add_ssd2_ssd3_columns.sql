-- Migration: Add SSD2 and SSD3 columns for multi-SSD support
-- Run this SQL in PostgreSQL to add the new columns

-- Add columns to computer_listings table
ALTER TABLE computer_listings 
    ADD COLUMN IF NOT EXISTS matched_ssd2_id INTEGER,
    ADD COLUMN IF NOT EXISTS matched_ssd3_id INTEGER,
    ADD COLUMN IF NOT EXISTS ssd2_confidence FLOAT,
    ADD COLUMN IF NOT EXISTS ssd3_confidence FLOAT,
    ADD COLUMN IF NOT EXISTS ssd2_match_method VARCHAR(50),
    ADD COLUMN IF NOT EXISTS ssd3_match_method VARCHAR(50);

-- Add columns to computer_listing_versions table (for version history)
ALTER TABLE computer_listing_versions 
    ADD COLUMN IF NOT EXISTS matched_ssd2_id INTEGER,
    ADD COLUMN IF NOT EXISTS matched_ssd3_id INTEGER,
    ADD COLUMN IF NOT EXISTS ssd2_confidence FLOAT,
    ADD COLUMN IF NOT EXISTS ssd3_confidence FLOAT;

-- Create indexes for the new columns (optional but recommended for queries)
CREATE INDEX IF NOT EXISTS idx_computer_listings_ssd2_id ON computer_listings(matched_ssd2_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_ssd3_id ON computer_listings(matched_ssd3_id);

-- Verify the columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'computer_listings' 
AND column_name IN ('matched_ssd2_id', 'matched_ssd3_id', 'ssd2_confidence', 'ssd3_confidence', 'ssd2_match_method', 'ssd3_match_method')
ORDER BY column_name;
