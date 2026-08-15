-- Debug lenses API issue
-- Check if listings exist and API works

-- Count lens listings
SELECT COUNT(*) as total_lens_listings 
FROM listings 
WHERE category = 'lens';

-- Check if any have images
SELECT COUNT(*) as with_images 
FROM listings 
WHERE category = 'lens' 
AND image_url IS NOT NULL;

-- Sample lens listings
SELECT listing_id, title, price_eur, category, is_active
FROM listings 
WHERE category = 'lens'
LIMIT 5;

-- Check lens_reference table
SELECT COUNT(*) as lens_refs FROM lens_reference;

-- Check if lens_confidence_score column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'listings' 
AND column_name LIKE '%lens%';
