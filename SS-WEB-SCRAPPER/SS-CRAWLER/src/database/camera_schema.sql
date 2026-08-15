-- Camera Reference Schema
-- Run this SQL to add camera body reference table

-- Camera Models Reference Table
CREATE TABLE IF NOT EXISTS camera_reference (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(200) NOT NULL,
    model_original VARCHAR(200),
    mount VARCHAR(100),
    sensor VARCHAR(100),
    camera_type VARCHAR(100),
    category VARCHAR(100),
    release_year INTEGER,
    resolution VARCHAR(100),
    fps VARCHAR(50),
    iso VARCHAR(100),
    focus_points VARCHAR(50),
    video_specs TEXT,
    battery VARCHAR(50),
    storage VARCHAR(100),
    screen VARCHAR(100),
    evf VARCHAR(100),
    has_raw BOOLEAN DEFAULT FALSE,
    has_clog BOOLEAN DEFAULT FALSE,
    has_clog2 BOOLEAN DEFAULT FALSE,
    has_clog3 BOOLEAN DEFAULT FALSE,
    has_slog BOOLEAN DEFAULT FALSE,
    has_slog2 BOOLEAN DEFAULT FALSE,
    has_slog3 BOOLEAN DEFAULT FALSE,
    has_4k BOOLEAN DEFAULT FALSE,
    has_8k BOOLEAN DEFAULT FALSE,
    sd_type VARCHAR(100),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Create indexes for camera reference
CREATE INDEX IF NOT EXISTS idx_camera_brand ON camera_reference(brand);
CREATE INDEX IF NOT EXISTS idx_camera_mount ON camera_reference(mount);
CREATE INDEX IF NOT EXISTS idx_camera_type ON camera_reference(camera_type);
CREATE INDEX IF NOT EXISTS idx_camera_category ON camera_reference(category);
CREATE INDEX IF NOT EXISTS idx_camera_keywords ON camera_reference USING GIN(search_keywords);

-- Add camera matching columns to listings table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='matched_camera_id') THEN
        ALTER TABLE listings ADD COLUMN matched_camera_id INTEGER REFERENCES camera_reference(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='camera_confidence_score') THEN
        ALTER TABLE listings ADD COLUMN camera_confidence_score DECIMAL(4,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='camera_match_method') THEN
        ALTER TABLE listings ADD COLUMN camera_match_method VARCHAR(50);
    END IF;
END $$;

-- Create indexes for camera columns
CREATE INDEX IF NOT EXISTS idx_listings_camera ON listings(matched_camera_id) WHERE matched_camera_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_listings_camera_category ON listings(category) WHERE category = 'camera';

-- View for camera listings with model info
CREATE OR REPLACE VIEW camera_listings_view AS
SELECT 
    l.listing_id,
    l.title,
    l.description,
    l.price_eur,
    l.seller_location,
    l.date_posted,
    l.is_active,
    l.camera_confidence_score,
    l.camera_match_method,
    c.brand,
    c.model,
    c.model_original,
    c.mount,
    c.sensor,
    c.camera_type,
    c.category,
    c.release_year,
    c.resolution,
    c.has_4k,
    c.has_8k
FROM listings l
LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
WHERE l.category = 'camera';

-- Function to get camera stats by brand
CREATE OR REPLACE FUNCTION get_camera_brand_stats(
    p_time_filter TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    brand TEXT,
    listing_count BIGINT,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.brand::TEXT,
        COUNT(*)::BIGINT as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2)::DECIMAL as avg_price,
        MIN(l.price_eur)::DECIMAL as min_price,
        MAX(l.price_eur)::DECIMAL as max_price
    FROM listings l
    JOIN camera_reference c ON l.matched_camera_id = c.id
    WHERE l.category = 'camera'
        AND l.is_active = true
        AND l.camera_confidence_score >= 0.50
        AND (p_time_filter = 'all_time' OR 
             (p_time_filter = 'week' AND l.date_posted > NOW() - INTERVAL '7 days') OR
             (p_time_filter = 'month' AND l.date_posted > NOW() - INTERVAL '30 days') OR
             (p_time_filter = 'year' AND l.date_posted > NOW() - INTERVAL '1 year'))
    GROUP BY c.brand
    ORDER BY listing_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get camera stats by model
CREATE OR REPLACE FUNCTION get_camera_model_stats(
    p_time_filter TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    brand TEXT,
    model TEXT,
    listing_count BIGINT,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.brand::TEXT,
        c.model::TEXT,
        COUNT(*)::BIGINT as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2)::DECIMAL as avg_price,
        MIN(l.price_eur)::DECIMAL as min_price,
        MAX(l.price_eur)::DECIMAL as max_price
    FROM listings l
    JOIN camera_reference c ON l.matched_camera_id = c.id
    WHERE l.category = 'camera'
        AND l.is_active = true
        AND l.camera_confidence_score >= 0.50
        AND (p_time_filter = 'all_time' OR 
             (p_time_filter = 'week' AND l.date_posted > NOW() - INTERVAL '7 days') OR
             (p_time_filter = 'month' AND l.date_posted > NOW() - INTERVAL '30 days') OR
             (p_time_filter = 'year' AND l.date_posted > NOW() - INTERVAL '1 year'))
    GROUP BY c.brand, c.model
    ORDER BY listing_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Table for listing flags (for debugging scraper errors)
CREATE TABLE IF NOT EXISTS listing_flags (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(50) REFERENCES listings(listing_id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL,  -- 'incorrect_match', 'missing_info', 'spam', 'other'
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_listing_flags_listing ON listing_flags(listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_flags_type ON listing_flags(flag_type);
CREATE INDEX IF NOT EXISTS idx_listing_flags_resolved ON listing_flags(resolved);
