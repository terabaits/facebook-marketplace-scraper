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
    local_image_path TEXT,
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
    recorded_at TIMESTAMP DEFAULT NOW(),
    change_type VARCHAR(100)  -- e.g., "price", "title", "description", "match"
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

-- PassMark GPU benchmark reference linking table
CREATE TABLE IF NOT EXISTS gpu_reference_passmark (
    id SERIAL PRIMARY KEY,
    gpu_reference_id INTEGER REFERENCES gpu_reference(id),
    passmark_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(300),
    g3d_mark INTEGER,
    g2d_mark INTEGER,
    tdp_w INTEGER,
    vram_mb INTEGER,
    category VARCHAR(100),
    bus_interface VARCHAR(100),
    max_memory_mb INTEGER,
    core_clock_mhz INTEGER,
    mem_clock_mhz INTEGER,
    rank INTEGER,
    samples INTEGER,
    price_usd DECIMAL(10,2),
    release_date VARCHAR(50),
    passmark_href VARCHAR(500),
    match_score DECIMAL(6,2),
    match_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gpu_passmark_ref_id ON gpu_reference_passmark(gpu_reference_id);
CREATE INDEX IF NOT EXISTS idx_gpu_passmark_passmark_id ON gpu_reference_passmark(passmark_id);
CREATE INDEX IF NOT EXISTS idx_gpu_passmark_name ON gpu_reference_passmark(name);

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

-- RAM Reference from ram.csv
CREATE TABLE IF NOT EXISTS ram_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    speed VARCHAR(50) NOT NULL,
    modules VARCHAR(50),
    first_word_latency DECIMAL(4,2),
    cas_latency INTEGER,
    rating INTEGER,
    price DECIMAL(10,2),
    capacity_gb INTEGER,
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Index for RAM reference
CREATE INDEX IF NOT EXISTS idx_ram_keywords ON ram_reference USING GIN(search_keywords);

-- Add RAM matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_ram_id INTEGER REFERENCES ram_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS ram_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS ram_match_method VARCHAR(50);

-- Case Reference from cases.csv
CREATE TABLE IF NOT EXISTS case_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    type VARCHAR(100),
    color VARCHAR(100),
    power_supply VARCHAR(100),
    side_panel VARCHAR(100),
    external_volume DECIMAL(10,2),
    internal_35_bays INTEGER,
    rating INTEGER,
    price DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Index for Case reference
CREATE INDEX IF NOT EXISTS idx_case_keywords ON case_reference USING GIN(search_keywords);

-- Add Case matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_case_id INTEGER REFERENCES case_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS case_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS case_match_method VARCHAR(50);

-- PSU Reference from psu.csv
CREATE TABLE IF NOT EXISTS psu_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    form_factor VARCHAR(50),
    efficiency_rating VARCHAR(50),
    wattage INTEGER,
    modular VARCHAR(50),
    rating INTEGER,
    price DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Index for PSU reference
CREATE INDEX IF NOT EXISTS idx_psu_keywords ON psu_reference USING GIN(search_keywords);

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
    special_features TEXT,
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

-- Insert basic console data (you can expand this)
INSERT INTO console_reference (name, company, generation, search_keywords, normalized_name) VALUES
    ('PlayStation 5', 'Sony', 5, ARRAY['ps5', 'playstation5', 'play station 5', 'sony ps5'], 'playstation 5'),
    ('PlayStation 4', 'Sony', 4, ARRAY['ps4', 'playstation4', 'play station 4', 'sony ps4'], 'playstation 4'),
    ('Xbox Series X', 'Microsoft', 9, ARRAY['xbox series x', 'xbox x', 'series x'], 'xbox series x'),
    ('Xbox Series S', 'Microsoft', 9, ARRAY['xbox series s', 'xbox s', 'series s'], 'xbox series s'),
    ('Xbox One', 'Microsoft', 8, ARRAY['xbox one', 'xboxone'], 'xbox one'),
    ('Nintendo Switch', 'Nintendo', 8, ARRAY['switch', 'nintendo switch', 'switch oled'], 'nintendo switch'),
    ('Nintendo Switch OLED', 'Nintendo', 8, ARRAY['switch oled', 'nintendo switch oled', 'oled switch'], 'nintendo switch oled')
ON CONFLICT DO NOTHING;

-- Add PSU matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_psu_id INTEGER REFERENCES psu_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS psu_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS psu_match_method VARCHAR(50);
-- Laptop listings table (raw collection before mobile CPU/GPU reference tables exist)
CREATE TABLE IF NOT EXISTS laptop_listings (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    price_eur DECIMAL(10,2) NOT NULL,
    seller_location VARCHAR(200),
    listing_url TEXT NOT NULL,
    image_url TEXT,
    local_image_path TEXT,
    date_posted TIMESTAMP,

    -- Structured fields extracted from SS.com options table
    brand VARCHAR(100),              -- Marka
    model VARCHAR(200),              -- Modelis
    display_size VARCHAR(50),        -- Displejs
    cpu_raw VARCHAR(200),            -- Procesors
    cpu_freq_ghz VARCHAR(50),        -- Procesora frekvence
    ram_gb INTEGER,                  -- Operatīvā atmiņa
    storage_gb INTEGER,              -- HDD apjoms
    storage_type VARCHAR(50),        -- ssd/hdd/emmc derived from description
    gpu_raw VARCHAR(200),            -- extracted from description
    condition_state VARCHAR(50),     -- Stavoklis (jauns/lietota)

    -- Lifecycle / source
    source VARCHAR(50) DEFAULT 'ss.com',
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),

    -- Duplication / versioning
    content_hash VARCHAR(64),
    previous_listing_id VARCHAR(50) REFERENCES laptop_listings(listing_id)
);

-- Price history for laptop listings
CREATE TABLE IF NOT EXISTS laptop_price_history (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) REFERENCES laptop_listings(listing_id) ON DELETE CASCADE,
    price_eur DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW(),
    change_type VARCHAR(100)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_laptop_listings_active ON laptop_listings(is_active);
CREATE INDEX IF NOT EXISTS idx_laptop_listings_brand ON laptop_listings(brand);
CREATE INDEX IF NOT EXISTS idx_laptop_listings_cpu_raw ON laptop_listings(cpu_raw);
CREATE INDEX IF NOT EXISTS idx_laptop_listings_gpu_raw ON laptop_listings(gpu_raw);
CREATE INDEX IF NOT EXISTS idx_laptop_listings_last_seen ON laptop_listings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_laptop_listings_content_hash ON laptop_listings(content_hash);
CREATE INDEX IF NOT EXISTS idx_laptop_price_history_listing ON laptop_price_history(listing_id);

-- Auto-update updated_at trigger
DROP TRIGGER IF EXISTS update_laptop_listings_updated_at ON laptop_listings;
CREATE TRIGGER update_laptop_listings_updated_at
    BEFORE UPDATE ON laptop_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
