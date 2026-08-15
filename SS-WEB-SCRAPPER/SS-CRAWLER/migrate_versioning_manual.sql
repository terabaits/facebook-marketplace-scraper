-- Manual Database Migration for Listing Versioning
-- Run these commands in order via pgAdmin or psql
-- This is safer for large tables that may cause timeouts

-- =============================================================================
-- STEP 1: listings table
-- =============================================================================

-- Check current state
SELECT 'listings' as table_name, 
       COUNT(*) as row_count,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='listings' AND column_name='version_number') as has_version,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='listings' AND column_name='content_fingerprint') as has_fingerprint;

-- Add version_number column (only if not exists)
ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;

-- Update existing rows (this may take time on large tables)
UPDATE listings SET version_number = 1 WHERE version_number IS NULL;

-- Make NOT NULL
ALTER TABLE listings ALTER COLUMN version_number SET NOT NULL;

-- Add content_fingerprint column
ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check existing constraints
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'listings'::regclass;

-- Drop old unique constraint on listing_id (replace 'listings_listing_id_key' with actual name from above)
-- ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_listing_id_key;

-- Add new composite unique constraint
ALTER TABLE listings 
ADD CONSTRAINT listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_listings_id_version ON listings(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_listings_fingerprint ON listings(content_fingerprint);

-- =============================================================================
-- STEP 2: computer_listings table
-- =============================================================================

-- Check current state
SELECT 'computer_listings' as table_name,
       COUNT(*) as row_count,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='computer_listings' AND column_name='version_number') as has_version,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='computer_listings' AND column_name='content_fingerprint') as has_fingerprint
FROM computer_listings;

-- Add version_number column
ALTER TABLE computer_listings 
ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;

-- Update existing rows
UPDATE computer_listings SET version_number = 1 WHERE version_number IS NULL;

-- Make NOT NULL
ALTER TABLE computer_listings ALTER COLUMN version_number SET NOT NULL;

-- Add content_fingerprint column
ALTER TABLE computer_listings 
ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check constraints
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'computer_listings'::regclass;

-- Drop old unique constraint (uncomment and replace with actual name)
-- ALTER TABLE computer_listings DROP CONSTRAINT IF EXISTS computer_listings_listing_id_key;

-- Add new composite unique constraint
ALTER TABLE computer_listings 
ADD CONSTRAINT computer_listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_computer_listings_id_version ON computer_listings(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_computer_listings_fingerprint ON computer_listings(content_fingerprint);

-- =============================================================================
-- STEP 3: console_listings table
-- =============================================================================

-- Check current state
SELECT 'console_listings' as table_name,
       COUNT(*) as row_count,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='console_listings' AND column_name='version_number') as has_version,
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='console_listings' AND column_name='content_fingerprint') as has_fingerprint
FROM console_listings;

-- Add version_number column
ALTER TABLE console_listings 
ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;

-- Update existing rows
UPDATE console_listings SET version_number = 1 WHERE version_number IS NULL;

-- Make NOT NULL
ALTER TABLE console_listings ALTER COLUMN version_number SET NOT NULL;

-- Add content_fingerprint column
ALTER TABLE console_listings 
ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check constraints
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'console_listings'::regclass;

-- Drop old unique constraint (uncomment and replace with actual name)
-- ALTER TABLE console_listings DROP CONSTRAINT IF EXISTS console_listings_listing_id_key;

-- Add new composite unique constraint
ALTER TABLE console_listings 
ADD CONSTRAINT console_listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_console_listings_id_version ON console_listings(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_console_listings_fingerprint ON console_listings(content_fingerprint);

-- =============================================================================
-- STEP 4: Create version history tables
-- =============================================================================

-- Main listing_versions table
CREATE TABLE IF NOT EXISTS listing_versions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    title VARCHAR(500),
    description TEXT,
    price_eur DECIMAL(10,2),
    seller_location VARCHAR(200),
    matched_gpu_id INTEGER,
    matched_cpu_id INTEGER,
    matched_ssd_id INTEGER,
    matched_ram_id INTEGER,
    matched_case_id INTEGER,
    matched_psu_id INTEGER,
    confidence_score DECIMAL(4,2),
    cpu_confidence_score DECIMAL(4,2),
    ssd_confidence_score DECIMAL(4,2),
    ram_confidence_score DECIMAL(4,2),
    case_confidence_score DECIMAL(4,2),
    psu_confidence_score DECIMAL(4,2),
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(listing_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_listing_versions_lookup ON listing_versions(listing_id, version_number);

-- Computer listing versions
CREATE TABLE IF NOT EXISTS computer_listing_versions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    title VARCHAR(500),
    description TEXT,
    price_eur DECIMAL(10,2),
    seller_location VARCHAR(200),
    matched_cpu_id INTEGER,
    matched_gpu_id INTEGER,
    matched_ram_id INTEGER,
    matched_ssd_id INTEGER,
    matched_ssd2_id INTEGER,
    matched_ssd3_id INTEGER,
    matched_psu_id INTEGER,
    matched_case_id INTEGER,
    cpu_confidence DECIMAL(4,2),
    gpu_confidence DECIMAL(4,2),
    ram_confidence DECIMAL(4,2),
    ssd_confidence DECIMAL(4,2),
    ssd2_confidence DECIMAL(4,2),
    ssd3_confidence DECIMAL(4,2),
    psu_confidence DECIMAL(4,2),
    case_confidence DECIMAL(4,2),
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(listing_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_computer_listing_versions_lookup ON computer_listing_versions(listing_id, version_number);

-- Console listing versions
CREATE TABLE IF NOT EXISTS console_listing_versions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    title VARCHAR(500),
    description TEXT,
    price_eur DECIMAL(10,2),
    seller_location VARCHAR(200),
    matched_console_id INTEGER,
    matched_variant_id INTEGER,
    matched_edition_id INTEGER,
    console_confidence_score DECIMAL(4,2),
    variant_confidence_score DECIMAL(4,2),
    edition_confidence_score DECIMAL(4,2),
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(listing_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_console_listing_versions_lookup ON console_listing_versions(listing_id, version_number);

-- =============================================================================
-- VERIFICATION
-- =============================================================================

SELECT 'Migration complete!' as status;

-- Check all tables have the new columns
SELECT 
    table_name,
    EXISTS (SELECT 1 FROM information_schema.columns 
            WHERE table_name=t.table_name AND column_name='version_number') as has_version,
    EXISTS (SELECT 1 FROM information_schema.columns 
            WHERE table_name=t.table_name AND column_name='content_fingerprint') as has_fingerprint
FROM (VALUES ('listings'), ('computer_listings'), ('console_listings')) as t(table_name);
