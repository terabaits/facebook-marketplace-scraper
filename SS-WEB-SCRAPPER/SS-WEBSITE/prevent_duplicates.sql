-- Add unique constraint to prevent duplicates
-- WARNING: Run this only after cleaning existing duplicates!

-- First, create a unique index on content (not listing_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_unique_content 
ON listings (title, price_eur, seller_location) 
WHERE is_active = true;

-- Alternative: Use a partial index that only applies to active listings
-- This allows historical duplicates to exist but prevents new active duplicates

-- If you want to allow the same listing to be re-activated with different IDs,
-- use this trigger approach instead:

CREATE OR REPLACE FUNCTION prevent_duplicate_active_listings()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if an active listing with same content exists
    IF EXISTS (
        SELECT 1 FROM listings 
        WHERE title = NEW.title 
          AND price_eur = NEW.price_eur 
          AND seller_location = NEW.seller_location
          AND category = NEW.category
          AND is_active = true
          AND id != NEW.id
    ) THEN
        -- Instead of inserting, update the existing one
        UPDATE listings 
        SET 
            listing_id = NEW.listing_id,
            listing_url = NEW.listing_url,
            last_seen_at = NOW(),
            is_active = true
        WHERE title = NEW.title 
          AND price_eur = NEW.price_eur 
          AND seller_location = NEW.seller_location
          AND category = NEW.category
          AND is_active = true;
        
        -- Cancel the insert
        RETURN NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS tr_prevent_duplicates ON listings;
CREATE TRIGGER tr_prevent_duplicates
    BEFORE INSERT ON listings
    FOR EACH ROW
    EXECUTE FUNCTION prevent_duplicate_active_listings();

COMMENT ON FUNCTION prevent_duplicate_active_listings() IS 
'Prevents duplicate active listings by updating existing record instead of inserting new one';
