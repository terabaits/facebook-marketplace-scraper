-- GPU Reference from cards.csv
CREATE TABLE IF NOT EXISTS gpu_reference (
    id SERIAL PRIMARY KEY,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(200) NOT NULL,
    raw_model VARCHAR(200),
    gpu_chip VARCHAR(100),
    vram_gb INTEGER,
    memory_type VARCHAR(50),
    year_released INTEGER,
    msrp_usd DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- CPU Reference from cpus.csv
CREATE TABLE IF NOT EXISTS cpu_reference (
    id SERIAL PRIMARY KEY,
    producer VARCHAR(50) NOT NULL,
    cpu_name VARCHAR(200) NOT NULL,
    processor_number VARCHAR(100) NOT NULL,
    brand_modifier VARCHAR(50),
    generation VARCHAR(50),
    cores INTEGER,
    p_cores INTEGER,
    e_cores INTEGER,
    threads INTEGER,
    max_turbo_freq DECIMAL(4,2),
    base_freq DECIMAL(4,2),
    cache_mb INTEGER,
    tdp_w INTEGER,
    socket VARCHAR(50),
    integrated_graphics VARCHAR(100),
    year_released INTEGER,
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Listings (core table, lean) - supports both GPU and CPU
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    price_eur DECIMAL(10,2) NOT NULL,
    seller_location VARCHAR(200),
    listing_url TEXT NOT NULL,
    image_url TEXT,
    date_posted TIMESTAMP,
    category VARCHAR(20) DEFAULT 'gpu',  -- 'gpu' or 'cpu'
    
    -- Matching for GPU
    matched_gpu_id INTEGER REFERENCES gpu_reference(id),
    confidence_score DECIMAL(4,2),
    match_method VARCHAR(50),
    
    -- Matching for CPU
    matched_cpu_id INTEGER REFERENCES cpu_reference(id),
    
    -- Lifecycle tracking
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Re-list detection
    content_hash VARCHAR(64),
    previous_listing_id VARCHAR(50) REFERENCES listings(listing_id),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Price history (separate table, append-only)
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) REFERENCES listings(listing_id) ON DELETE CASCADE,
    price_eur DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Debug snapshots (separate from main table)
CREATE TABLE IF NOT EXISTS debug_snapshots (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50),
    fetched_at TIMESTAMP DEFAULT NOW(),
    html_content TEXT,
    parse_error TEXT,
    url TEXT
);

-- Scraping runs (with proper status tracking)
CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    category VARCHAR(50),
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    updated_listings INTEGER DEFAULT 0,
    skipped_unchanged INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    config_snapshot JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_last_seen ON listings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_listings_content_hash ON listings(content_hash);
CREATE INDEX IF NOT EXISTS idx_listings_gpu ON listings(matched_gpu_id);
CREATE INDEX IF NOT EXISTS idx_listings_cpu ON listings(matched_cpu_id);
CREATE INDEX IF NOT EXISTS idx_listings_category ON listings(category);
CREATE INDEX IF NOT EXISTS idx_price_history_listing ON price_history(listing_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_listing ON debug_snapshots(listing_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_time ON debug_snapshots(fetched_at);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_listings_updated_at ON listings;
CREATE TRIGGER update_listings_updated_at
    BEFORE UPDATE ON listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- GIN index for text array search
CREATE INDEX IF NOT EXISTS idx_gpu_keywords ON gpu_reference USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_cpu_keywords ON cpu_reference USING GIN(search_keywords);

-- SSD Reference from SSD.csv
CREATE TABLE IF NOT EXISTS ssd_reference (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(200) NOT NULL,
    interface VARCHAR(100),
    form_factor VARCHAR(50),
    capacity_gb INTEGER,
    controller VARCHAR(100),
    configuration VARCHAR(100),
    has_dram BOOLEAN,
    hmb VARCHAR(50),
    nand_brand VARCHAR(50),
    nand_type VARCHAR(50),
    layers VARCHAR(50),
    read_speed_mb INTEGER,
    write_speed_mb INTEGER,
    category VARCHAR(100),
    notes TEXT,
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Index for SSD reference
CREATE INDEX IF NOT EXISTS idx_ssd_keywords ON ssd_reference USING GIN(search_keywords);

-- Add SSD matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_ssd_id INTEGER REFERENCES ssd_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS ssd_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS ssd_match_method VARCHAR(50);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS capacity_gb INTEGER; -- extracted from listing
