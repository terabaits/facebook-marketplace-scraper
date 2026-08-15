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

-- Import CPU reference data from cpus.csv
-- Create temp table for CSV import
DROP TABLE IF EXISTS temp_cpus;
CREATE TEMP TABLE temp_cpus (
    producer TEXT,
    cpu_name TEXT,
    processor_number TEXT,
    brand_modifier TEXT,
    generation TEXT,
    cores TEXT,
    p_cores TEXT,
    e_cores TEXT,
    threads TEXT,
    max_turbo_freq TEXT,
    base_freq TEXT,
    cache_mb TEXT,
    tdp_w TEXT,
    socket TEXT,
    integrated_graphics TEXT,
    year TEXT
);

-- Copy from CSV
COPY temp_cpus FROM '/data/cpus.csv' WITH (FORMAT csv, HEADER true);

-- Insert with keyword generation
INSERT INTO cpu_reference (
    producer, cpu_name, processor_number, brand_modifier, generation,
    cores, p_cores, e_cores, threads, max_turbo_freq, base_freq,
    cache_mb, tdp_w, socket, integrated_graphics, year_released,
    search_keywords, normalized_name
)
SELECT 
    TRIM(producer) as producer,
    TRIM(cpu_name) as cpu_name,
    TRIM(processor_number) as processor_number,
    NULLIF(TRIM(brand_modifier), '') as brand_modifier,
    NULLIF(TRIM(generation), '') as generation,
    CASE WHEN cores ~ '^[0-9]+$' THEN cores::INTEGER ELSE NULL END as cores,
    CASE WHEN p_cores ~ '^[0-9]+$' THEN p_cores::INTEGER ELSE NULL END as p_cores,
    CASE WHEN e_cores ~ '^[0-9]+$' THEN e_cores::INTEGER ELSE NULL END as e_cores,
    CASE WHEN threads ~ '^[0-9]+$' THEN threads::INTEGER ELSE NULL END as threads,
    CASE WHEN max_turbo_freq ~ '^[0-9]+\.?[0-9]*$' THEN max_turbo_freq::DECIMAL(4,2) ELSE NULL END as max_turbo_freq,
    CASE WHEN base_freq ~ '^[0-9]+\.?[0-9]*$' THEN base_freq::DECIMAL(4,2) ELSE NULL END as base_freq,
    CASE WHEN cache_mb ~ '^[0-9]+$' THEN cache_mb::INTEGER ELSE NULL END as cache_mb,
    CASE WHEN tdp_w ~ '^[0-9]+$' THEN tdp_w::INTEGER ELSE NULL END as tdp_w,
    NULLIF(TRIM(socket), '') as socket,
    NULLIF(TRIM(integrated_graphics), '') as integrated_graphics,
    CASE WHEN year ~ '^[0-9]{4}$' THEN year::INTEGER ELSE NULL END as year_released,
    -- Generate search keywords array
    ARRAY[
        LOWER(TRIM(processor_number)),
        LOWER(TRIM(cpu_name)),
        LOWER(TRIM(producer)) || ' ' || LOWER(TRIM(processor_number)),
        LOWER(REGEXP_REPLACE(cpu_name, '[^a-zA-Z0-9]', '', 'g'))
    ] as search_keywords,
    LOWER(REGEXP_REPLACE(processor_number, '[^a-zA-Z0-9]', '', 'g')) as normalized_name
FROM temp_cpus
WHERE cpu_name IS NOT NULL AND TRIM(cpu_name) != '';

-- Clean up temp table
DROP TABLE IF EXISTS temp_cpus;

-- Log import results
DO $$
DECLARE
    cpu_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO cpu_count FROM cpu_reference;
    RAISE NOTICE 'Imported % CPU models into cpu_reference table', cpu_count;
END $$;
