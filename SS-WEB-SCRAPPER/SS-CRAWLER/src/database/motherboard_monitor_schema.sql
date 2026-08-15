-- Motherboard and Monitor Schema Additions
-- Run this SQL to add tables for the new categories

-- Motherboard Models Reference Table
CREATE TABLE IF NOT EXISTS motherboard_models (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(200) NOT NULL,
    socket VARCHAR(50),
    chipset VARCHAR(100),
    ram_slots VARCHAR(50),
    form_factor VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Index for motherboard reference
CREATE INDEX IF NOT EXISTS idx_motherboard_brand ON motherboard_models(brand);
CREATE INDEX IF NOT EXISTS idx_motherboard_chipset ON motherboard_models(chipset);
CREATE INDEX IF NOT EXISTS idx_motherboard_keywords ON motherboard_models USING GIN(search_keywords);

-- Monitor Models Reference Table
CREATE TABLE IF NOT EXISTS monitor_models (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(200) NOT NULL,
    size VARCHAR(20),
    resolution VARCHAR(50),
    refresh_rate VARCHAR(20),
    panel_type VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(300) NOT NULL
);

-- Index for monitor reference
CREATE INDEX IF NOT EXISTS idx_monitor_brand ON monitor_models(brand);
CREATE INDEX IF NOT EXISTS idx_monitor_size ON monitor_models(size);
CREATE INDEX IF NOT EXISTS idx_monitor_resolution ON monitor_models(resolution);
CREATE INDEX IF NOT EXISTS idx_monitor_keywords ON monitor_models USING GIN(search_keywords);

-- Add motherboard matching columns to listings table (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='motherboard_model_id') THEN
        ALTER TABLE listings ADD COLUMN motherboard_model_id INTEGER REFERENCES motherboard_models(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='motherboard_confidence_score') THEN
        ALTER TABLE listings ADD COLUMN motherboard_confidence_score DECIMAL(4,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='motherboard_match_method') THEN
        ALTER TABLE listings ADD COLUMN motherboard_match_method VARCHAR(50);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='monitor_model_id') THEN
        ALTER TABLE listings ADD COLUMN monitor_model_id INTEGER REFERENCES monitor_models(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='monitor_confidence_score') THEN
        ALTER TABLE listings ADD COLUMN monitor_confidence_score DECIMAL(4,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='monitor_match_method') THEN
        ALTER TABLE listings ADD COLUMN monitor_match_method VARCHAR(50);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='is_special_listing') THEN
        ALTER TABLE listings ADD COLUMN is_special_listing BOOLEAN DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='listings' AND column_name='special_listing_reason') THEN
        ALTER TABLE listings ADD COLUMN special_listing_reason VARCHAR(255);
    END IF;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_listings_motherboard ON listings(motherboard_model_id) WHERE motherboard_model_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_listings_monitor ON listings(monitor_model_id) WHERE monitor_model_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_listings_motherboard_category ON listings(category) WHERE category = 'motherboard';
CREATE INDEX IF NOT EXISTS idx_listings_monitor_category ON listings(category) WHERE category = 'monitor';

-- View for motherboard listings with model info
CREATE OR REPLACE VIEW motherboard_listings_view AS
SELECT 
    l.listing_id,
    l.title,
    l.description,
    l.price_eur,
    l.seller_location,
    l.date_posted,
    l.is_active,
    l.motherboard_confidence_score,
    l.motherboard_match_method,
    m.brand,
    m.model,
    m.socket,
    m.chipset,
    m.ram_slots,
    m.form_factor
FROM listings l
LEFT JOIN motherboard_models m ON l.motherboard_model_id = m.id
WHERE l.category = 'motherboard';

-- View for monitor listings with model info
CREATE OR REPLACE VIEW monitor_listings_view AS
SELECT 
    l.listing_id,
    l.title,
    l.description,
    l.price_eur,
    l.seller_location,
    l.date_posted,
    l.is_active,
    l.monitor_confidence_score,
    l.monitor_match_method,
    m.brand,
    m.model,
    m.size,
    m.resolution,
    m.refresh_rate,
    m.panel_type
FROM listings l
LEFT JOIN monitor_models m ON l.monitor_model_id = m.id
WHERE l.category = 'monitor';

-- Function to get motherboard chipset popularity
CREATE OR REPLACE FUNCTION get_motherboard_chipset_stats(
    p_time_filter TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    chipset TEXT,
    listing_count BIGINT,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.chipset::TEXT,
        COUNT(*)::BIGINT as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2)::DECIMAL as avg_price,
        MIN(l.price_eur)::DECIMAL as min_price,
        MAX(l.price_eur)::DECIMAL as max_price
    FROM listings l
    JOIN motherboard_models m ON l.motherboard_model_id = m.id
    WHERE l.category = 'motherboard'
        AND l.is_active = true
        AND l.motherboard_confidence_score >= 0.70
        AND (p_time_filter = 'all_time' OR 
             (p_time_filter = 'week' AND l.date_posted > NOW() - INTERVAL '7 days') OR
             (p_time_filter = 'month' AND l.date_posted > NOW() - INTERVAL '30 days') OR
             (p_time_filter = 'year' AND l.date_posted > NOW() - INTERVAL '1 year'))
    GROUP BY m.chipset
    ORDER BY listing_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get monitor stats by size
CREATE OR REPLACE FUNCTION get_monitor_size_stats(
    p_time_filter TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    size TEXT,
    listing_count BIGINT,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.size::TEXT,
        COUNT(*)::BIGINT as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2)::DECIMAL as avg_price,
        MIN(l.price_eur)::DECIMAL as min_price,
        MAX(l.price_eur)::DECIMAL as max_price
    FROM listings l
    JOIN monitor_models m ON l.monitor_model_id = m.id
    WHERE l.category = 'monitor'
        AND l.is_active = true
        AND l.monitor_confidence_score >= 0.70
        AND (p_time_filter = 'all_time' OR 
             (p_time_filter = 'week' AND l.date_posted > NOW() - INTERVAL '7 days') OR
             (p_time_filter = 'month' AND l.date_posted > NOW() - INTERVAL '30 days') OR
             (p_time_filter = 'year' AND l.date_posted > NOW() - INTERVAL '1 year'))
    GROUP BY m.size
    ORDER BY listing_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get monitor stats by resolution
CREATE OR REPLACE FUNCTION get_monitor_resolution_stats(
    p_time_filter TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    resolution TEXT,
    listing_count BIGINT,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.resolution::TEXT,
        COUNT(*)::BIGINT as listing_count,
        ROUND(AVG(l.price_eur)::numeric, 2)::DECIMAL as avg_price,
        MIN(l.price_eur)::DECIMAL as min_price,
        MAX(l.price_eur)::DECIMAL as max_price
    FROM listings l
    JOIN monitor_models m ON l.monitor_model_id = m.id
    WHERE l.category = 'monitor'
        AND l.is_active = true
        AND l.monitor_confidence_score >= 0.70
        AND (p_time_filter = 'all_time' OR 
             (p_time_filter = 'week' AND l.date_posted > NOW() - INTERVAL '7 days') OR
             (p_time_filter = 'month' AND l.date_posted > NOW() - INTERVAL '30 days') OR
             (p_time_filter = 'year' AND l.date_posted > NOW() - INTERVAL '1 year'))
    GROUP BY m.resolution
    ORDER BY listing_count DESC;
END;
$$ LANGUAGE plpgsql;
