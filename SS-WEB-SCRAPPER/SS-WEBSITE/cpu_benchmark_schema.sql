-- =====================================================
-- CPU Benchmark Database Schema
-- Creates separate tables for benchmark data without modifying CPU_REFERENCE
-- =====================================================

-- 1. Cinebench R23 Scores Table
CREATE TABLE IF NOT EXISTS cpu_benchmarks_r23 (
    id SERIAL PRIMARY KEY,
    cpu_name VARCHAR(255) NOT NULL,
    cinebench_r23_single INTEGER,
    cinebench_r23_multi INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cpu_name)
);

-- 2. Cinebench 2026 Scores Table  
CREATE TABLE IF NOT EXISTS cpu_benchmarks_r26 (
    id SERIAL PRIMARY KEY,
    cpu_name VARCHAR(255) NOT NULL,
    cinebench_r26_single INTEGER,
    cinebench_r26_multi INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cpu_name)
);

-- 3. PassMark Benchmark Table
CREATE TABLE IF NOT EXISTS cpu_benchmarks_passmark (
    id SERIAL PRIMARY KEY,
    cpu_name VARCHAR(255) NOT NULL,
    socket VARCHAR(100),
    clock_speed VARCHAR(50),
    turbo_speed VARCHAR(50),
    cores INTEGER,
    threads INTEGER,
    tdp VARCHAR(50),
    passmark_score INTEGER,
    source_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cpu_name)
);

-- 4. PCPartPicker Prices Table
CREATE TABLE IF NOT EXISTS cpu_prices_pcpartpicker (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    core_count INTEGER,
    base_clock VARCHAR(50),
    boost_clock VARCHAR(50),
    microarchitecture VARCHAR(100),
    integrated_graphics VARCHAR(100),
    smt BOOLEAN,
    tdp INTEGER,
    rating INTEGER,
    price_eur DECIMAL(10,2),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- 5. Name Matching Links Table (fuzzy matching results)
CREATE TABLE IF NOT EXISTS cpu_name_matches (
    id SERIAL PRIMARY KEY,
    cpu_reference_id INTEGER REFERENCES cpu_reference(id),
    r23_cpu_name VARCHAR(255),
    r26_cpu_name VARCHAR(255),
    passmark_cpu_name VARCHAR(255),
    pcpartpicker_name VARCHAR(255),
    match_confidence DECIMAL(3,2),
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cpu_reference_id)
);

-- 6. Complete CPU Data View
CREATE OR REPLACE VIEW cpu_complete_data AS
SELECT 
    cr.id AS cpu_reference_id,
    cr.producer,
    cr.cpu_name,
    cr.processor_number,
    cr.cores,
    cr.threads,
    cr.base_freq,
    cr.socket,
    cr.tdp_w,
    
    -- Cinebench R23
    r23.cinebench_r23_single,
    r23.cinebench_r23_multi,
    CASE WHEN r23.cinebench_r23_multi IS NOT NULL 
         THEN ROUND(r23.cinebench_r23_multi::DECIMAL / NULLIF(cr.threads, 0), 2)
         ELSE NULL 
    END AS r23_per_thread,
    
    -- Cinebench 2026
    r26.cinebench_r26_single,
    r26.cinebench_r26_multi,
    
    -- PassMark
    pm.passmark_score,
    pm.clock_speed AS passmark_clock,
    pm.tdp AS passmark_tdp,
    
    -- PCPartPicker Prices
    pp.price_eur AS pcpartpicker_price,
    pp.rating AS pcpartpicker_rating,
    
    -- Match Status
    CASE 
        WHEN r23.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_r23,
    CASE 
        WHEN r26.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_r26,
    CASE 
        WHEN pm.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_passmark,
    CASE 
        WHEN pp.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_pcpartpicker,
    
    -- Total match score (0-4)
    (CASE WHEN r23.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN r26.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pm.id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN pp.id IS NOT NULL THEN 1 ELSE 0 END) AS data_completeness_score

FROM cpu_reference cr
LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
LEFT JOIN cpu_benchmarks_r23 r23 ON cnm.r23_cpu_name = r23.cpu_name
LEFT JOIN cpu_benchmarks_r26 r26 ON cnm.r26_cpu_name = r26.cpu_name  
LEFT JOIN cpu_benchmarks_passmark pm ON cnm.passmark_cpu_name = pm.cpu_name
LEFT JOIN cpu_prices_pcpartpicker pp ON cnm.pcpartpicker_name = pp.name;

-- 7. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cpu_ref_name ON cpu_reference(normalized_name);
CREATE INDEX IF NOT EXISTS idx_r23_name ON cpu_benchmarks_r23(cpu_name);
CREATE INDEX IF NOT EXISTS idx_r26_name ON cpu_benchmarks_r26(cpu_name);
CREATE INDEX IF NOT EXISTS idx_passmark_name ON cpu_benchmarks_passmark(cpu_name);
CREATE INDEX IF NOT EXISTS idx_pcpp_name ON cpu_prices_pcpartpicker(name);
CREATE INDEX IF NOT EXISTS idx_matches_ref ON cpu_name_matches(cpu_reference_id);

-- 8. Analytics Views

-- Unmatched CPUs View
CREATE OR REPLACE VIEW cpu_unmatched_analysis AS
SELECT 
    cr.id,
    cr.producer,
    cr.cpu_name,
    cr.processor_number,
    CASE 
        WHEN cnm.cpu_reference_id IS NULL THEN 'No matches found'
        ELSE 'Partial match'
    END AS match_status
FROM cpu_reference cr
LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
WHERE cnm.cpu_reference_id IS NULL 
   OR (cnm.r23_cpu_name IS NULL AND cnm.r26_cpu_name IS NULL 
       AND cnm.passmark_cpu_name IS NULL AND cnm.pcpartpicker_name IS NULL);

-- CPUs with Multiple Potential Matches
CREATE OR REPLACE VIEW cpu_multiple_matches AS
SELECT 
    cr.id,
    cr.cpu_name,
    COUNT(*) AS match_count,
    STRING_AGG(DISTINCT cnm_alt.r23_cpu_name, ', ') AS matched_names
FROM cpu_reference cr
JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
LEFT JOIN cpu_name_matches cnm_alt ON (
    cnm.r23_cpu_name = cnm_alt.r23_cpu_name 
    AND cnm.cpu_reference_id != cnm_alt.cpu_reference_id
)
WHERE cnm_alt.cpu_reference_id IS NOT NULL
GROUP BY cr.id, cr.cpu_name
HAVING COUNT(*) > 1;

-- Match Success Rate Summary
CREATE OR REPLACE VIEW cpu_match_summary AS
SELECT 
    'Cinebench R23' AS source,
    COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
    (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
    ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / (SELECT COUNT(*) FROM cpu_reference), 2) AS match_percentage
FROM cpu_name_matches cnm
WHERE cnm.r23_cpu_name IS NOT NULL

UNION ALL

SELECT 
    'Cinebench 2026' AS source,
    COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
    (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
    ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / (SELECT COUNT(*) FROM cpu_reference), 2) AS match_percentage
FROM cpu_name_matches cnm
WHERE cnm.r26_cpu_name IS NOT NULL

UNION ALL

SELECT 
    'PassMark' AS source,
    COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
    (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
    ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / (SELECT COUNT(*) FROM cpu_reference), 2) AS match_percentage
FROM cpu_name_matches cnm
WHERE cnm.passmark_cpu_name IS NOT NULL

UNION ALL

SELECT 
    'PCPartPicker Prices' AS source,
    COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
    (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
    ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / (SELECT COUNT(*) FROM cpu_reference), 2) AS match_percentage
FROM cpu_name_matches cnm
WHERE cnm.pcpartpicker_name IS NOT NULL

UNION ALL

SELECT 
    'At least one source' AS source,
    COUNT(DISTINCT cpu_reference_id) AS matched_count,
    (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
    ROUND(COUNT(DISTINCT cpu_reference_id) * 100.0 / (SELECT COUNT(*) FROM cpu_reference), 2) AS match_percentage
FROM cpu_name_matches;
