-- Console Schema with Versioning Support

-- Console Reference table - base console information
CREATE TABLE IF NOT EXISTS console_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(50),
    generation INTEGER,
    release_date VARCHAR(100),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Variant table - specific models/revisions
CREATE TABLE IF NOT EXISTS console_variants (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    sku VARCHAR(50),
    storage_gb INTEGER,
    region VARCHAR(50),
    release_date VARCHAR(100),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Edition table - special colors/bundles
CREATE TABLE IF NOT EXISTS console_editions (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES console_variants(id) ON DELETE SET NULL,
    edition_name VARCHAR(200) NOT NULL,
    color VARCHAR(100),
    special_features TEXT,
    msrp_usd DECIMAL(10,2),
    msrp_eur DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Listings table with versioning
CREATE TABLE IF NOT EXISTS console_listings (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL,  -- Base ID like 'gexxm'
    version_number INTEGER DEFAULT 1,  -- Version for reused IDs
    title VARCHAR(500) NOT NULL,
    description TEXT,
    price_eur DECIMAL(10,2) NOT NULL,
    seller_location VARCHAR(200),
    listing_url TEXT NOT NULL,
    image_url TEXT,
    local_image_path TEXT,
    date_posted TIMESTAMP,
    
    -- Matching references
    matched_console_id INTEGER REFERENCES console_reference(id),
    matched_variant_id INTEGER REFERENCES console_variants(id),
    matched_edition_id INTEGER REFERENCES console_editions(id),
    
    -- Confidence and matching info
    console_confidence_score DECIMAL(4,2),
    console_match_method VARCHAR(50),
    variant_confidence_score DECIMAL(4,2),
    variant_match_method VARCHAR(50),
    edition_confidence_score DECIMAL(4,2),
    edition_match_method VARCHAR(50),
    
    -- Special edition flag
    is_special_edition BOOLEAN DEFAULT FALSE,
    special_edition_note TEXT,
    
    -- Lifecycle tracking
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Content fingerprint for versioning detection
    content_hash VARCHAR(64),
    content_fingerprint VARCHAR(64),
    
    -- Unique constraint on ID + version
    UNIQUE(listing_id, version_number)
);

-- Console Scraper Log (CSL)
CREATE TABLE IF NOT EXISTS console_scraper_log (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER,
    listing_id VARCHAR(50),
    version_number INTEGER DEFAULT 1,
    title TEXT,
    matched_console_name VARCHAR(100),
    matched_variant_name VARCHAR(100),
    matched_edition_name VARCHAR(200),
    confidence_console DECIMAL(4,2),
    confidence_variant DECIMAL(4,2),
    confidence_edition DECIMAL(4,2),
    match_method VARCHAR(50),
    special_flag BOOLEAN DEFAULT FALSE,
    special_note TEXT,
    logged_at TIMESTAMP DEFAULT NOW()
);

-- Price history for consoles
CREATE TABLE IF NOT EXISTS console_price_history (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL,
    version_number INTEGER DEFAULT 1,
    price_eur DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW(),
    change_type VARCHAR(100)
);

-- Console listing versions (history)
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

-- Scraping runs for consoles
CREATE TABLE IF NOT EXISTS console_scrape_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    category VARCHAR(50) DEFAULT 'consoles',
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    updated_listings INTEGER DEFAULT 0,
    skipped_unchanged INTEGER DEFAULT 0,
    new_versions INTEGER DEFAULT 0,  -- Track new versions created
    failed_requests INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    config_snapshot JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_console_listings_active ON console_listings(is_active);
CREATE INDEX IF NOT EXISTS idx_console_listings_last_seen ON console_listings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_console_listings_content_hash ON console_listings(content_hash);
CREATE INDEX IF NOT EXISTS idx_console_listings_fingerprint ON console_listings(content_fingerprint);
CREATE INDEX IF NOT EXISTS idx_console_listings_id_version ON console_listings(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_console_listings_console ON console_listings(matched_console_id);
CREATE INDEX IF NOT EXISTS idx_console_listings_variant ON console_listings(matched_variant_id);
CREATE INDEX IF NOT EXISTS idx_console_listings_edition ON console_listings(matched_edition_id);
CREATE INDEX IF NOT EXISTS idx_console_keywords ON console_reference USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_variant_keywords ON console_variants USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_edition_keywords ON console_editions USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_scraper_log_listing ON console_scraper_log(listing_id);
CREATE INDEX IF NOT EXISTS idx_console_scraper_log_time ON console_scraper_log(logged_at);
CREATE INDEX IF NOT EXISTS idx_console_price_history_listing ON console_price_history(listing_id, version_number);
CREATE INDEX IF NOT EXISTS idx_console_listing_versions ON console_listing_versions(listing_id, version_number);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_console_listings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_console_listings_updated_at_trigger ON console_listings;
CREATE TRIGGER update_console_listings_updated_at_trigger
    BEFORE UPDATE ON console_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_console_listings_updated_at();
