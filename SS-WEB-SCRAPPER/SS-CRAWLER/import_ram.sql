-- Import RAM reference data from ram.csv
-- Run this inside the container: docker exec -i ss_crawler_db psql -U crawler -d ss_market < import_ram.sql

-- Create temp table
DROP TABLE IF EXISTS temp_ram;
CREATE TEMP TABLE temp_ram (
    name TEXT,
    speed TEXT,
    modules TEXT,
    first_word_latency TEXT,
    cas_latency TEXT,
    rating TEXT,
    price TEXT
);

-- Copy raw data
COPY temp_ram FROM '/data/ram.csv' WITH (FORMAT csv, HEADER true);

-- Transform and insert
INSERT INTO ram_reference (
    name, speed, modules, first_word_latency, cas_latency, rating, price,
    capacity_gb, search_keywords, normalized_name
)
SELECT 
    TRIM(name) as name,
    TRIM(speed) as speed,
    TRIM(modules) as modules,
    CASE 
        WHEN first_word_latency ~ '^[0-9]+\.?[0-9]*$' THEN first_word_latency::DECIMAL(4,2)
        ELSE NULL 
    END as first_word_latency,
    CASE 
        WHEN cas_latency ~ '^[0-9]+$' THEN cas_latency::INTEGER 
        ELSE NULL 
    END as cas_latency,
    CASE 
        WHEN rating ~ '^[0-9]+$' THEN rating::INTEGER 
        ELSE NULL 
    END as rating,
    CASE 
        WHEN price ~ '[0-9]' THEN CAST(regexp_replace(price, '[^0-9.]', '', 'g') AS DECIMAL(10,2))
        ELSE NULL 
    END as price,
    -- Extract capacity from name
    CASE 
        WHEN name ~ '([0-9]+)\s*GB' THEN CAST(SUBSTRING(name FROM '([0-9]+)\s*GB') AS INTEGER)
        ELSE NULL 
    END as capacity_gb,
    -- Generate search keywords
    ARRAY[
        LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]', '', 'g')),
        LOWER(TRIM(name)),
        LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]', ' ', 'g')),
        LOWER(TRIM(speed))
    ] as search_keywords,
    LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]', '', 'g')) as normalized_name
FROM temp_ram
WHERE name IS NOT NULL AND TRIM(name) != '';

-- Clean up
DROP TABLE IF EXISTS temp_ram;

-- Report
SELECT COUNT(*) as imported_count FROM ram_reference;
