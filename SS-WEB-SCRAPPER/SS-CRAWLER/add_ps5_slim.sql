-- Add PlayStation 5 Slim to console_reference
INSERT INTO console_reference (id, name, company, generation, normalized_name, release_year, discontinued)
VALUES (27, 'PlayStation 5 Slim', 'Sony', 9, 'playstation 5 slim', 2023, false);

-- Add variants for PS5 Slim
INSERT INTO console_variants (console_id, model_name, sku, storage_gb, normalized_name, search_keywords)
VALUES 
    (27, 'PlayStation 5 Slim', 'Slim', 1024, 'playstation 5 slim', ARRAY['slim', 'ps5 slim', 'playstation 5 slim']),
    (27, 'PlayStation 5 Slim Digital', 'Slim Digital', 1024, 'playstation 5 slim digital', ARRAY['slim digital', 'ps5 slim digital']);
