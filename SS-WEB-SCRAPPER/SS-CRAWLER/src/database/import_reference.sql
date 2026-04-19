-- Import GPU reference data from cards.csv
-- This runs automatically when PostgreSQL starts for the first time

-- Create temp table for CSV import
DROP TABLE IF EXISTS temp_cards;
CREATE TEMP TABLE temp_cards (
    vendor TEXT,
    model TEXT,
    raw TEXT,
    raw_model TEXT,
    clockspeed TEXT,
    gpu TEXT,
    memory TEXT,
    buswidth TEXT,
    mflops TEXT,
    max_bandwidth TEXT,
    directx TEXT,
    memory_type TEXT,
    process_size TEXT,
    transistors TEXT,
    bus_slot TEXT,
    external_power TEXT,
    msrp TEXT,
    year TEXT
);

-- Copy from CSV
COPY temp_cards FROM '/data/cards.csv' WITH (FORMAT csv, HEADER true);

-- Insert with keyword generation
INSERT INTO gpu_reference (
    vendor, model, raw_model, gpu_chip, vram_gb, memory_type,
    year_released, msrp_usd, search_keywords, normalized_name
)
SELECT 
    UPPER(TRIM(vendor)) as vendor,
    TRIM(model) as model,
    TRIM(raw_model) as raw_model,
    TRIM(gpu) as gpu_chip,
    CASE 
        WHEN memory ~ '^[0-9]+$' THEN memory::INTEGER 
        ELSE NULL 
    END as vram_gb,
    TRIM(memory_type) as memory_type,
    CASE 
        WHEN year ~ '^[0-9]{4}$' THEN year::INTEGER 
        ELSE NULL 
    END as year_released,
    CASE 
        WHEN msrp ~ '[0-9]' THEN CAST(regexp_replace(msrp, '[^0-9.]', '', 'g') AS DECIMAL(10,2))
        ELSE NULL 
    END as msrp_usd,
    -- Generate search keywords array
    ARRAY[
        LOWER(REGEXP_REPLACE(model, '[^a-zA-Z0-9]', '', 'g')),
        LOWER(TRIM(model)),
        LOWER(TRIM(vendor)) || ' ' || LOWER(REGEXP_REPLACE(model, '[^a-zA-Z0-9]', '', 'g')),
        LOWER(REGEXP_REPLACE(model, '[^a-zA-Z0-9]', ' ', 'g'))  -- spaced version
    ] as search_keywords,
    LOWER(REGEXP_REPLACE(model, '[^a-zA-Z0-9]', '', 'g')) as normalized_name
FROM temp_cards
WHERE model IS NOT NULL AND TRIM(model) != '';

-- Clean up temp table
DROP TABLE IF EXISTS temp_cards;

-- Log import results
DO $$
DECLARE
    gpu_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO gpu_count FROM gpu_reference;
    RAISE NOTICE 'Imported % GPU models into gpu_reference table', gpu_count;
END $$;
