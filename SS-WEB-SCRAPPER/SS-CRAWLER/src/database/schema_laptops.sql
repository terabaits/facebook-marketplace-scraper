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
    previous_listing_id VARCHAR(50) REFERENCES laptop_listings(listing_id),

    -- Link to the per-model reference (FK is enforced by the scraper, not the DB,
    -- so legacy listings and the backfill migration can both leave it NULL).
    laptop_reference_id INTEGER,

    -- Link to the canonical CPU reference. Points at `laptop_reference_cpu.id`
    -- so the spec window can show "i7-11400H" / "Ryzen 7 5800H" / "M2" even when
    -- the raw listing spelled it as "I7", "I5-1135g7", or "Amd ryzen 5".
    cpu_reference_id INTEGER
);

-- Canonical CPU reference for laptop listings. One row per unique
-- (brand, model) pair, e.g. ("Intel", "i7-11400H"). Populated by the
-- scraper via `CPUReferenceResolver` and backfilled from existing
-- laptop_listings.cpu_raw by `backfill_laptop_reference_cpu.py`.
CREATE TABLE IF NOT EXISTS laptop_reference_cpu (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(64) NOT NULL,
    model VARCHAR(128) NOT NULL,
    normalized_key VARCHAR(256) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_laptop_reference_cpu_key
    ON laptop_reference_cpu (normalized_key);

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
CREATE INDEX IF NOT EXISTS idx_laptop_listings_laptop_reference_id ON laptop_listings(laptop_reference_id) WHERE laptop_reference_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_laptop_listings_cpu_reference_id ON laptop_listings(cpu_reference_id) WHERE cpu_reference_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_laptop_price_history_listing ON laptop_price_history(listing_id);

-- Auto-update updated_at trigger
DROP TRIGGER IF EXISTS update_laptop_listings_updated_at ON laptop_listings;
CREATE TRIGGER update_laptop_listings_updated_at
    BEFORE UPDATE ON laptop_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
