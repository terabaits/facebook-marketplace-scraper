-- Facebook Scraper Extension Database Schema
-- Phase 1: Foundation

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== COMPONENT REFERENCE TABLES ====================

-- Parent table for all components
CREATE TABLE IF NOT EXISTS component_reference (
    id SERIAL PRIMARY KEY,
    component_type VARCHAR(20) NOT NULL CHECK (component_type IN ('gpu', 'cpu', 'ram', 'ssd', 'psu', 'motherboard', 'case')),
    full_name VARCHAR(200) NOT NULL,
    brand VARCHAR(50),
    msrp_usd DECIMAL(10,2),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(component_type, full_name)
);

-- GPU-specific table
CREATE TABLE IF NOT EXISTS gpu_details (
    component_id INTEGER PRIMARY KEY REFERENCES component_reference(id) ON DELETE CASCADE,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    vram_gb INTEGER,
    tdp_watts INTEGER,
    release_year INTEGER,
    
    -- Detection patterns
    aliases TEXT[],
    detection_patterns JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- CPU-specific table
CREATE TABLE IF NOT EXISTS cpu_details (
    component_id INTEGER PRIMARY KEY REFERENCES component_reference(id) ON DELETE CASCADE,
    producer VARCHAR(50) NOT NULL,
    processor_number VARCHAR(50) NOT NULL,
    cpu_name VARCHAR(100),
    socket VARCHAR(50),
    cores INTEGER,
    threads INTEGER,
    base_freq DECIMAL(4,2),
    tdp_watts INTEGER,
    
    aliases TEXT[],
    detection_patterns JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- RAM-specific table
CREATE TABLE IF NOT EXISTS ram_details (
    component_id INTEGER PRIMARY KEY REFERENCES component_reference(id) ON DELETE CASCADE,
    name VARCHAR(200),
    ddr_type VARCHAR(10),
    capacity_gb INTEGER,
    speed_mhz INTEGER,
    
    detection_patterns JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- SSD-specific table
CREATE TABLE IF NOT EXISTS ssd_details (
    component_id INTEGER PRIMARY KEY REFERENCES component_reference(id) ON DELETE CASCADE,
    brand VARCHAR(100),
    model VARCHAR(200),
    capacity_gb INTEGER,
    interface VARCHAR(50),
    form_factor VARCHAR(20),
    
    detection_patterns JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==================== PRICE HISTORY ====================

CREATE TABLE IF NOT EXISTS component_price_history (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES component_reference(id) ON DELETE CASCADE,
    
    avg_price_eur DECIMAL(10,2) NOT NULL,
    min_price_eur DECIMAL(10,2),
    max_price_eur DECIMAL(10,2),
    sample_count INTEGER,
    
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(component_id, period_start)
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_price_history_component 
ON component_price_history(component_id, period_start DESC);

-- ==================== DETECTION CACHE ====================

CREATE TABLE IF NOT EXISTS detection_cache (
    id SERIAL PRIMARY KEY,
    text_hash VARCHAR(64) NOT NULL,
    detection_version VARCHAR(10) NOT NULL,
    
    components JSONB NOT NULL,
    confidence DECIMAL(3,2),
    
    hit_count INTEGER DEFAULT 1,
    last_hit_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(text_hash, detection_version)
);

CREATE INDEX IF NOT EXISTS idx_detection_cache_lookup 
ON detection_cache(text_hash, detection_version);

CREATE INDEX IF NOT EXISTS idx_detection_cache_expires 
ON detection_cache(expires_at);

-- ==================== TELEMETRY (PRIVACY-PRESERVING) ====================

CREATE TABLE IF NOT EXISTS extension_telemetry (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    
    -- Request ID (not traceable to user)
    request_id UUID,
    
    -- Timing only
    processing_time_ms INTEGER,
    
    -- Component counts only (not actual models)
    components_detected_count INTEGER,
    component_types TEXT[],
    
    -- Cache performance
    cache_hit BOOLEAN,
    
    -- Selector performance (no DOM content)
    selector_strategy VARCHAR(50),
    selector_success BOOLEAN,
    selector_time_ms INTEGER,
    
    -- Error info (no sensitive data)
    error_code VARCHAR(50),
    error_category VARCHAR(50),
    
    -- System info
    extension_version VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_telemetry_event 
ON extension_telemetry(event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_time 
ON extension_telemetry(processing_time_ms, created_at);

-- ==================== CACHE INVALIDATION FUNCTION ====================

CREATE OR REPLACE FUNCTION invalidate_cache_version(old_version VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM detection_cache 
    WHERE detection_version = old_version;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==================== SAMPLE DATA (Phase 1) ====================

-- Insert sample GPUs
INSERT INTO component_reference (component_type, full_name, brand)
VALUES 
    ('gpu', 'NVIDIA GeForce RTX 3080', 'NVIDIA'),
    ('gpu', 'NVIDIA GeForce RTX 3070', 'NVIDIA'),
    ('gpu', 'NVIDIA GeForce RTX 3060 Ti', 'NVIDIA'),
    ('gpu', 'AMD Radeon RX 6800 XT', 'AMD'),
    ('gpu', 'AMD Radeon RX 6700 XT', 'AMD')
ON CONFLICT (component_type, full_name) DO NOTHING;

-- Insert GPU details
INSERT INTO gpu_details (component_id, vendor, model, vram_gb, release_year, aliases)
SELECT 
    cr.id,
    CASE 
        WHEN cr.full_name LIKE '%NVIDIA%' THEN 'NVIDIA'
        WHEN cr.full_name LIKE '%AMD%' THEN 'AMD'
    END,
    SPLIT_PART(cr.full_name, ' ', 4),
    CASE 
        WHEN cr.full_name LIKE '%3080%' THEN 10
        WHEN cr.full_name LIKE '%3070%' THEN 8
        WHEN cr.full_name LIKE '%3060%' THEN 8
        WHEN cr.full_name LIKE '%6800%' THEN 16
        WHEN cr.full_name LIKE '%6700%' THEN 12
    END,
    2020,
    CASE 
        WHEN cr.full_name LIKE '%3080%' THEN ARRAY['rtx 3080', '3080', 'rtx3080', '3080ti', '3080 ti']
        WHEN cr.full_name LIKE '%3070%' THEN ARRAY['rtx 3070', '3070', 'rtx3070']
        WHEN cr.full_name LIKE '%3060%' THEN ARRAY['rtx 3060 ti', '3060ti', 'rtx 3060', '3060']
        WHEN cr.full_name LIKE '%6800%' THEN ARRAY['rx 6800 xt', '6800xt', 'rx 6800', '6800']
        WHEN cr.full_name LIKE '%6700%' THEN ARRAY['rx 6700 xt', '6700xt', 'rx 6700', '6700']
    END
FROM component_reference cr
WHERE cr.component_type = 'gpu'
ON CONFLICT (component_id) DO NOTHING;

-- Insert sample CPUs
INSERT INTO component_reference (component_type, full_name, brand)
VALUES 
    ('cpu', 'Intel Core i7-12700K', 'Intel'),
    ('cpu', 'Intel Core i5-12400', 'Intel'),
    ('cpu', 'AMD Ryzen 5 5600X', 'AMD'),
    ('cpu', 'AMD Ryzen 7 5800X', 'AMD')
ON CONFLICT (component_type, full_name) DO NOTHING;

-- Insert CPU details
INSERT INTO cpu_details (component_id, producer, processor_number, cpu_name, socket, cores, threads, aliases)
SELECT 
    cr.id,
    CASE 
        WHEN cr.full_name LIKE '%Intel%' THEN 'Intel'
        WHEN cr.full_name LIKE '%AMD%' THEN 'AMD'
    END,
    SPLIT_PART(cr.full_name, '-', 2),
    SPLIT_PART(cr.full_name, ' ', 3),
    CASE 
        WHEN cr.full_name LIKE '%12%' THEN 'LGA 1700'
        WHEN cr.full_name LIKE '%5600%' OR cr.full_name LIKE '%5800%' THEN 'AM4'
    END,
    CASE 
        WHEN cr.full_name LIKE '%i7%' THEN 12
        WHEN cr.full_name LIKE '%i5%' THEN 6
        WHEN cr.full_name LIKE '%5600%' THEN 6
        WHEN cr.full_name LIKE '%5800%' THEN 8
    END,
    CASE 
        WHEN cr.full_name LIKE '%i7%' THEN 20
        WHEN cr.full_name LIKE '%i5%' THEN 12
        WHEN cr.full_name LIKE '%5600%' THEN 12
        WHEN cr.full_name LIKE '%5800%' THEN 16
    END,
    CASE 
        WHEN cr.full_name LIKE '%12700%' THEN ARRAY['i7-12700k', '12700k', 'i7 12700k']
        WHEN cr.full_name LIKE '%12400%' THEN ARRAY['i5-12400', '12400', 'i5 12400']
        WHEN cr.full_name LIKE '%5600%' THEN ARRAY['ryzen 5 5600x', '5600x', 'r5 5600x']
        WHEN cr.full_name LIKE '%5800%' THEN ARRAY['ryzen 7 5800x', '5800x', 'r7 5800x']
    END
FROM component_reference cr
WHERE cr.component_type = 'cpu'
ON CONFLICT (component_id) DO NOTHING;

-- Insert sample RAM
INSERT INTO component_reference (component_type, full_name, brand)
VALUES 
    ('ram', 'DDR4 16GB 3200MHz', 'Generic'),
    ('ram', 'DDR4 32GB 3600MHz', 'Generic'),
    ('ram', 'DDR5 32GB 5600MHz', 'Generic')
ON CONFLICT (component_type, full_name) DO NOTHING;

-- Insert RAM details
INSERT INTO ram_details (component_id, name, ddr_type, capacity_gb, speed_mhz)
SELECT 
    cr.id,
    cr.full_name,
    SPLIT_PART(cr.full_name, ' ', 1),
    (regexp_match(cr.full_name, '(\d+)GB'))[1]::INTEGER,
    (regexp_match(cr.full_name, '(\d+)MHz'))[1]::INTEGER
FROM component_reference cr
WHERE cr.component_type = 'ram'
ON CONFLICT (component_id) DO NOTHING;

COMMIT;

-- Print summary
SELECT 'Schema created successfully' AS status;
SELECT COUNT(*) AS component_count FROM component_reference;
SELECT component_type, COUNT(*) AS count FROM component_reference GROUP BY component_type;
