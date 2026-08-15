-- Apply lens schema to database
-- Run this in psql or use the Python script

\echo 'Creating lens_reference table...'

CREATE TABLE IF NOT EXISTS lens_reference (
    id SERIAL PRIMARY KEY,
    system VARCHAR(50) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    range_type VARCHAR(50),
    lens_type VARCHAR(50),
    mount VARCHAR(50) NOT NULL,
    lens_name VARCHAR(200) NOT NULL,
    focal_length_mm INTEGER,
    max_focal_length_mm INTEGER,
    max_aperture VARCHAR(20),
    filter_mm INTEGER,
    min_focus_distance_cm INTEGER,
    diameter_mm INTEGER,
    length_mm INTEGER,
    weight_g INTEGER,
    has_is BOOLEAN DEFAULT FALSE,
    has_wr BOOLEAN DEFAULT FALSE,
    elements INTEGER,
    blades INTEGER,
    price_new DECIMAL(10,2),
    release_date DATE,
    notes TEXT,
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_lens_brand ON lens_reference(brand);
CREATE INDEX IF NOT EXISTS idx_lens_mount ON lens_reference(mount);
CREATE INDEX IF NOT EXISTS idx_lens_focal ON lens_reference(focal_length_mm);
CREATE INDEX IF NOT EXISTS idx_lens_normalized ON lens_reference(normalized_name);
CREATE INDEX IF NOT EXISTS idx_lens_name ON lens_reference(lens_name);

-- Add GIN index for array search
CREATE INDEX IF NOT EXISTS idx_lens_keywords ON lens_reference USING GIN(search_keywords);

\echo 'Lens reference table created successfully!'

-- Verify table structure
\d lens_reference
