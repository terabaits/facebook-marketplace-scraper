-- Fix console_listings sequence
SELECT setval('console_listings_id_seq', COALESCE((SELECT MAX(id) FROM console_listings), 0) + 1, false);

-- Fix other sequences that might have the same issue
SELECT setval('listings_id_seq', COALESCE((SELECT MAX(id) FROM listings), 0) + 1, false);
SELECT setval('computer_listings_id_seq', COALESCE((SELECT MAX(id) FROM computer_listings), 0) + 1, false);
SELECT setval('scrape_runs_id_seq', COALESCE((SELECT MAX(id) FROM scrape_runs), 0) + 1, false);
