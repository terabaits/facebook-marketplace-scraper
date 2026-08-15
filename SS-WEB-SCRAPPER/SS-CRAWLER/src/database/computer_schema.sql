-- Computer Listings Schema
-- Table for storing scraped PC listings with component detection

CREATE TABLE IF NOT EXISTS computer_listings (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    price_eur DECIMAL(10,2) NOT NULL,
    seller_location VARCHAR(200),
    listing_url TEXT NOT NULL,
    image_url TEXT,
    date_posted TIMESTAMP,
    
    -- Component matches
    matched_cpu_id INTEGER REFERENCES cpu_reference(id),
    matched_gpu_id INTEGER REFERENCES gpu_reference(id),
    matched_ram_id INTEGER REFERENCES ram_reference(id),
    matched_ssd_id INTEGER REFERENCES ssd_reference(id),
    matched_psu_id INTEGER REFERENCES psu_reference(id),
    matched_case_id INTEGER REFERENCES case_reference(id),
    
    -- Fallback/Generic component assignments
    fallback_psu_wattage INTEGER,  -- 400 or 650 when no PSU mentioned
    fallback_case_price DECIMAL(10,2) DEFAULT 15.00,  -- €15 generic case
    fallback_motherboard_price DECIMAL(10,2),  -- Entry-level motherboard based on CPU socket
    
    -- Confidence scores for each component
    cpu_confidence DECIMAL(4,2),
    gpu_confidence DECIMAL(4,2),
    ram_confidence DECIMAL(4,2),
    ssd_confidence DECIMAL(4,2),
    psu_confidence DECIMAL(4,2),
    case_confidence DECIMAL(4,2),
    
    -- Match methods
    cpu_match_method VARCHAR(50),
    gpu_match_method VARCHAR(50),
    ram_match_method VARCHAR(50),
    ssd_match_method VARCHAR(50),
    psu_match_method VARCHAR(50),
    case_match_method VARCHAR(50),
    
    -- Flagging system
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    flag_comment TEXT,
    flagged_at TIMESTAMP,
    flagged_by VARCHAR(100),
    
    -- Calculated totals
    components_total_eur DECIMAL(10,2),
    price_difference_eur DECIMAL(10,2),  -- listing price - components_total
    
    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    
    -- Prebuilt vs custom build classification
    build_type VARCHAR(20) DEFAULT NULL,  -- prebuilt, custom, unknown
    is_prebuilt BOOLEAN DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Content hash for duplicate detection
    content_hash VARCHAR(64),
    previous_listing_id VARCHAR(50) REFERENCES computer_listings(listing_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_computer_listings_active ON computer_listings(is_active);
CREATE INDEX IF NOT EXISTS idx_computer_listings_last_seen ON computer_listings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_computer_listings_flagged ON computer_listings(is_flagged);
CREATE INDEX IF NOT EXISTS idx_computer_listings_cpu ON computer_listings(matched_cpu_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_gpu ON computer_listings(matched_gpu_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_ram ON computer_listings(matched_ram_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_ssd ON computer_listings(matched_ssd_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_psu ON computer_listings(matched_psu_id);
CREATE INDEX IF NOT EXISTS idx_computer_listings_case ON computer_listings(matched_case_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_computer_listings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_computer_listings_updated_at_trigger ON computer_listings;
CREATE TRIGGER update_computer_listings_updated_at_trigger
    BEFORE UPDATE ON computer_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_computer_listings_updated_at();

-- Computer listing versions (for history tracking)
CREATE TABLE IF NOT EXISTS computer_listing_versions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) NOT NULL REFERENCES computer_listings(listing_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(500),
    description TEXT,
    price_eur DECIMAL(10,2),
    seller_location VARCHAR(200),
    matched_cpu_id INTEGER,
    matched_gpu_id INTEGER,
    matched_ram_id INTEGER,
    matched_ssd_id INTEGER,
    matched_psu_id INTEGER,
    matched_case_id INTEGER,
    cpu_confidence DECIMAL(4,2),
    gpu_confidence DECIMAL(4,2),
    ram_confidence DECIMAL(4,2),
    ssd_confidence DECIMAL(4,2),
    psu_confidence DECIMAL(4,2),
    case_confidence DECIMAL(4,2),
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(listing_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_computer_listing_versions_listing ON computer_listing_versions(listing_id);