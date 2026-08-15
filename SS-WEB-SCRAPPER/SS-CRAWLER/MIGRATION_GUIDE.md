# Manual Migration Guide for Listing Versioning

The Python script is timing out due to the large `listings` table. Here's how to complete the migration manually.

## Quick Check

First, let's see what already completed from the Python script:

```sql
-- Check what columns exist
SELECT table_name, column_name 
FROM information_schema.columns 
WHERE table_name IN ('listings', 'computer_listings', 'console_listings') 
  AND column_name IN ('version_number', 'content_fingerprint')
ORDER BY table_name;
```

## If only `version_number` exists on `listings`:

### Step 1: Complete listings table
```sql
-- Add content_fingerprint column
ALTER TABLE listings ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check existing constraints (copy the constraint name)
SELECT conname FROM pg_constraint WHERE conrelid = 'listings'::regclass;

-- Drop the old unique constraint (replace xxx with actual name)
-- ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_listing_id_key;

-- Add new composite unique constraint
ALTER TABLE listings ADD CONSTRAINT listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

-- Create indexes
CREATE INDEX idx_listings_id_version ON listings(listing_id, version_number);
CREATE INDEX idx_listings_fingerprint ON listings(content_fingerprint);
```

### Step 2: Migrate computer_listings
```sql
ALTER TABLE computer_listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
UPDATE computer_listings SET version_number = 1 WHERE version_number IS NULL;
ALTER TABLE computer_listings ALTER COLUMN version_number SET NOT NULL;
ALTER TABLE computer_listings ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check and drop old constraint
-- ALTER TABLE computer_listings DROP CONSTRAINT IF EXISTS computer_listings_listing_id_key;

ALTER TABLE computer_listings ADD CONSTRAINT computer_listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

CREATE INDEX idx_computer_listings_id_version ON computer_listings(listing_id, version_number);
CREATE INDEX idx_computer_listings_fingerprint ON computer_listings(content_fingerprint);
```

### Step 3: Migrate console_listings
```sql
ALTER TABLE console_listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
UPDATE console_listings SET version_number = 1 WHERE version_number IS NULL;
ALTER TABLE console_listings ALTER COLUMN version_number SET NOT NULL;
ALTER TABLE console_listings ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);

-- Check and drop old constraint
-- ALTER TABLE console_listings DROP CONSTRAINT IF EXISTS console_listings_listing_id_key;

ALTER TABLE console_listings ADD CONSTRAINT console_listings_listing_id_version_unique 
UNIQUE (listing_id, version_number);

CREATE INDEX idx_console_listings_id_version ON console_listings(listing_id, version_number);
CREATE INDEX idx_console_listings_fingerprint ON console_listings(content_fingerprint);
```

### Step 4: Create version history tables
```sql
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
```

## Verification

```sql
-- Check all tables have the new columns
SELECT 
    table_name,
    EXISTS (SELECT 1 FROM information_schema.columns 
            WHERE table_name=t.table_name AND column_name='version_number') as has_version,
    EXISTS (SELECT 1 FROM information_schema.columns 
            WHERE table_name=t.table_name AND column_name='content_fingerprint') as has_fingerprint
FROM (VALUES ('listings'), ('computer_listings'), ('console_listings')) as t(table_name);
```

## Using pgAdmin

1. Open pgAdmin
2. Connect to your `ss_market` database
3. Open Query Tool
4. Run the commands above in order
5. Check for errors after each step

The SQL file `migrate_versioning_manual.sql` has all these commands ready to copy/paste.
