-- Add Patriot P210 128GB SATA SSD to ssd_reference table
-- This will be inserted with a new ID (after the existing max ID)

INSERT INTO ssd_reference (
    brand,
    model,
    interface,
    form_factor,
    capacity_gb,
    controller,
    configuration,
    has_dram,
    hmb,
    nand_brand,
    nand_type,
    layers,
    read_speed_mb,
    write_speed_mb,
    category,
    notes,
    search_keywords,
    normalized_name
) VALUES (
    'Patriot',
    'P210',
    'SATA/AHCI',
    '2.5"',
    128,
    NULL,  -- Controller unknown/variable
    NULL,
    FALSE,  -- No DRAM cache
    NULL,
    NULL,   -- NAND brand varies
    'TLC',  -- Typically TLC
    NULL,
    500,    -- Typical read speed for P210 128GB
    400,    -- Typical write speed
    'Entry-Level SATA',
    'Budget SATA SSD',
    ARRAY['patriot p210', 'p210', 'patriot', 'patriot p210 128gb', 'p210 128gb'],
    'patriot p210'
);

-- Verify insertion
SELECT * FROM ssd_reference WHERE brand = 'Patriot' AND model = 'P210';
