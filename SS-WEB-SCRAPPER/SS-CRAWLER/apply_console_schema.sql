-- Apply console tables to database
-- Run this in psql or pgAdmin

-- Console Reference (for game consoles like PlayStation, Xbox, Nintendo)
CREATE TABLE IF NOT EXISTS console_reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(50),
    generation INTEGER,
    release_date VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Variants (different models like PS5 Slim, PS5 Pro)
CREATE TABLE IF NOT EXISTS console_variants (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,
    sku VARCHAR(100),
    storage_gb INTEGER,
    region VARCHAR(50),
    release_date VARCHAR(50),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Console Editions (special colors, bundles)
CREATE TABLE IF NOT EXISTS console_editions (
    id SERIAL PRIMARY KEY,
    console_id INTEGER REFERENCES console_reference(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES console_variants(id) ON DELETE SET NULL,
    edition_name VARCHAR(200) NOT NULL,
    color VARCHAR(100),
    special_features TEXT,
    msrp_usd DECIMAL(10,2),
    msrp_eur DECIMAL(10,2),
    search_keywords TEXT[] NOT NULL DEFAULT '{}',
    normalized_name VARCHAR(200) NOT NULL
);

-- Add console matching columns to listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_console_id INTEGER REFERENCES console_reference(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_variant_id INTEGER REFERENCES console_variants(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS matched_edition_id INTEGER REFERENCES console_editions(id);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS console_confidence_score DECIMAL(4,2);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS console_match_method VARCHAR(50);

-- Indexes for console tables
CREATE INDEX IF NOT EXISTS idx_console_keywords ON console_reference USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_variant_keywords ON console_variants USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_console_edition_keywords ON console_editions USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_listings_console ON listings(matched_console_id);

-- Insert basic console data
INSERT INTO console_reference (name, company, generation, search_keywords, normalized_name) VALUES
    ('PlayStation 5', 'Sony', 5, ARRAY['ps5', 'playstation5', 'play station 5', 'sony ps5'], 'playstation 5'),
    ('PlayStation 4', 'Sony', 4, ARRAY['ps4', 'playstation4', 'play station 4', 'sony ps4'], 'playstation 4'),
    ('Xbox Series X', 'Microsoft', 9, ARRAY['xbox series x', 'xbox x', 'series x'], 'xbox series x'),
    ('Xbox Series S', 'Microsoft', 9, ARRAY['xbox series s', 'xbox s', 'series s'], 'xbox series s'),
    ('Xbox One', 'Microsoft', 8, ARRAY['xbox one', 'xboxone'], 'xbox one'),
    ('Nintendo Switch', 'Nintendo', 8, ARRAY['switch', 'nintendo switch', 'switch oled'], 'nintendo switch'),
    ('Nintendo Switch OLED', 'Nintendo', 8, ARRAY['switch oled', 'nintendo switch oled', 'oled switch'], 'nintendo switch oled')
ON CONFLICT DO NOTHING;

-- Insert console variants
INSERT INTO console_variants (console_id, model_name, storage_gb, search_keywords, normalized_name)
SELECT 
    cr.id,
    CASE 
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Standard' THEN 'PlayStation 5 Standard'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Digital' THEN 'PlayStation 5 Digital Edition'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Slim' THEN 'PlayStation 5 Slim'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Pro' THEN 'PlayStation 5 Pro'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Standard' THEN 'PlayStation 4'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Slim' THEN 'PlayStation 4 Slim'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Pro' THEN 'PlayStation 4 Pro'
        WHEN cr.name = 'Xbox Series X' THEN 'Xbox Series X'
        WHEN cr.name = 'Xbox Series S' THEN 'Xbox Series S'
        WHEN cr.name = 'Xbox One' AND m.model = 'Standard' THEN 'Xbox One'
        WHEN cr.name = 'Xbox One' AND m.model = 'S' THEN 'Xbox One S'
        WHEN cr.name = 'Xbox One' AND m.model = 'X' THEN 'Xbox One X'
        WHEN cr.name LIKE 'Nintendo Switch%' THEN cr.name
    END,
    m.storage,
    m.keywords,
    CASE 
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Standard' THEN 'playstation 5 standard'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Digital' THEN 'playstation 5 digital'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Slim' THEN 'playstation 5 slim'
        WHEN cr.name = 'PlayStation 5' AND m.model = 'Pro' THEN 'playstation 5 pro'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Standard' THEN 'playstation 4'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Slim' THEN 'playstation 4 slim'
        WHEN cr.name = 'PlayStation 4' AND m.model = 'Pro' THEN 'playstation 4 pro'
        WHEN cr.name = 'Xbox Series X' THEN 'xbox series x'
        WHEN cr.name = 'Xbox Series S' THEN 'xbox series s'
        WHEN cr.name = 'Xbox One' AND m.model = 'Standard' THEN 'xbox one'
        WHEN cr.name = 'Xbox One' AND m.model = 'S' THEN 'xbox one s'
        WHEN cr.name = 'Xbox One' AND m.model = 'X' THEN 'xbox one x'
        WHEN cr.name = 'Nintendo Switch' THEN 'nintendo switch'
        WHEN cr.name = 'Nintendo Switch OLED' THEN 'nintendo switch oled'
    END
FROM console_reference cr
CROSS JOIN LATERAL (
    VALUES 
        -- PS5 variants
        ('Standard', 825, ARRAY['ps5', 'playstation 5', '825gb']),
        ('Digital', 825, ARRAY['ps5 digital', 'playstation 5 digital', '825gb']),
        ('Slim', 1000, ARRAY['ps5 slim', 'playstation 5 slim']),
        ('Pro', NULL, ARRAY['ps5 pro', 'playstation 5 pro']),
        -- PS4 variants
        ('Standard', 500, ARRAY['ps4', 'playstation 4', '500gb']),
        ('Slim', 500, ARRAY['ps4 slim', 'playstation 4 slim']),
        ('Slim', 1000, ARRAY['ps4 slim', 'playstation 4 slim', '1tb']),
        ('Pro', 1000, ARRAY['ps4 pro', 'playstation 4 pro', '1tb']),
        -- Xbox Series
        ('Standard', 1000, ARRAY['xbox series x', 'series x']),
        ('Standard', 512, ARRAY['xbox series s', 'series s']),
        -- Xbox One variants
        ('Standard', 500, ARRAY['xbox one', '500gb']),
        ('S', 500, ARRAY['xbox one s', 'one s']),
        ('S', 1000, ARRAY['xbox one s', 'one s', '1tb']),
        ('X', 1000, ARRAY['xbox one x', 'one x']),
        -- Nintendo (dummy, will be filtered)
        ('Standard', 32, ARRAY['switch']),
        ('Standard', 64, ARRAY['switch oled'])
) AS m(model, storage, keywords)
WHERE (cr.name = 'PlayStation 5' AND m.model IN ('Standard', 'Digital', 'Slim', 'Pro'))
   OR (cr.name = 'PlayStation 4' AND m.model IN ('Standard', 'Slim', 'Pro'))
   OR (cr.name = 'Xbox Series X' AND m.model = 'Standard')
   OR (cr.name = 'Xbox Series S' AND m.model = 'Standard')
   OR (cr.name = 'Xbox One' AND m.model IN ('Standard', 'S', 'X'))
   OR (cr.name = 'Nintendo Switch' AND m.storage = 32)
   OR (cr.name = 'Nintendo Switch OLED' AND m.storage = 64)
ON CONFLICT DO NOTHING;

SELECT 'Console tables created successfully!' AS status;
