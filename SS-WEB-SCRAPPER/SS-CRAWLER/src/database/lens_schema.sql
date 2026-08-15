-- Lens Reference from lenses.csv
CREATE TABLE IF NOT EXISTS lens_reference (
    id SERIAL PRIMARY KEY,
    system VARCHAR(50) NOT NULL,           -- Canon, Sony, Nikon, etc.
    brand VARCHAR(50) NOT NULL,              -- Canon, Sigma, Tamron, etc.
    range_type VARCHAR(50),                  -- Prime, Zoom, Full frame, etc.
    lens_type VARCHAR(50),                   -- AF, MF, TS-E, SP, etc.
    mount VARCHAR(50) NOT NULL,              -- EF, RF, E, F, etc.
    lens_name VARCHAR(200) NOT NULL,         -- Full lens name like "24-105mm F4L IS USM"
    focal_length_mm INTEGER,                 -- Wide end focal length
    max_focal_length_mm INTEGER,             -- Tele end for zooms
    max_aperture VARCHAR(20),                -- "2.8", "4", "3.5-5.6", etc.
    filter_mm INTEGER,                       -- Filter thread size
    min_focus_distance_cm INTEGER,           -- MFD in cm
    diameter_mm INTEGER,                     -- Lens diameter
    length_mm INTEGER,                       -- Lens length
    weight_g INTEGER,                        -- Weight in grams
    has_is BOOLEAN,                          -- Image Stabilization
    has_wr BOOLEAN,                          -- Weather Resistance
    elements INTEGER,                        -- Number of lens elements
    blades INTEGER,                          -- Aperture blades
    price_new DECIMAL(10,2),                 -- MSRP/retail price
    release_date DATE,                       -- When lens was released
    notes TEXT,                              -- Additional notes
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Create indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_lens_brand ON lens_reference(brand);
CREATE INDEX IF NOT EXISTS idx_lens_mount ON lens_reference(mount);
CREATE INDEX IF NOT EXISTS idx_lens_focal ON lens_reference(focal_length_mm);
CREATE INDEX IF NOT EXISTS idx_lens_normalized ON lens_reference(normalized_name);

-- Add lens matching columns to listings table (if not already present)
-- These should already be added via lens_schema.sql from earlier work
-- DO NOT run this if columns already exist - check first

-- Alternative: lens-specific listing fields (extends listings table concept)
-- Using the columns already added to listings table:
-- matched_lens_id (VARCHAR) - stores the matched lens reference ID
-- lens_confidence_score (NUMERIC) - confidence of the match
-- lens_match_method (VARCHAR) - how the match was determined
