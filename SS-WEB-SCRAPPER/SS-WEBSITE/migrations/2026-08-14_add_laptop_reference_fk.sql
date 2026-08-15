-- Migration: link laptop_listings to laptop_reference via a real FK column.
--
-- Today the link is a "soft" join via a computed normalized_key expression in
-- every query (/api/laptops, /api/listing-details, etc). This works but:
--   * the join is slow and hard to index
--   * adding new listings through the scraper doesn't create a reference row
--   * the /api/laptops SELECT has to repeat the same CASE/REGEXP dance
--
-- After this migration:
--   * laptop_listings.laptop_reference_id is an indexed INT (no FK constraint
--     to keep the migration re-runnable; the scraper is the only writer)
--   * laptop_reference.normalized_key is re-derived for every row using the
--     same rules as `src/scraper/laptop_reference_resolver.py`, so a row
--     that no longer has a meaningful key is set to ''
--   * any rows that now share a normalized_key are collapsed: a winner is
--     picked (lowest id), losers are deleted
--   * laptop_listings.laptop_reference_id is backfilled from the (re-derived)
--     normalized_key. Listings whose brand/model is NULL end up with NULL FK.

-- 1. Add the FK column (no DB-level FK constraint yet; the scraper is the only
--    writer and we want the migration to be re-runnable).
ALTER TABLE laptop_listings
    ADD COLUMN IF NOT EXISTS laptop_reference_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_laptop_listings_laptop_reference_id
    ON laptop_listings (laptop_reference_id)
    WHERE laptop_reference_id IS NOT NULL;

-- 2. Re-derive normalized_key for every laptop_reference row.
--    To avoid violating the UNIQUE constraint during the rewrite, we drop the
--    unique index, do the rewrite (which may produce duplicates), collapse the
--    duplicates, then re-add the unique index.

ALTER TABLE laptop_reference DROP CONSTRAINT IF EXISTS laptop_reference_normalized_key_key;

UPDATE laptop_reference lr
SET normalized_key = COALESCE(
    NULLIF(
        -- brand
        lower(regexp_replace(regexp_replace(trim(COALESCE(brand, '')), '\s+', ' ', 'g'), '\s+', ' ', 'g'))
        -- model
        || '|' ||
        lower(regexp_replace(
            trim(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(trim(COALESCE(model, '')), '\([^)]*\)', '', 'g'),
                        '^\s*(klēpjdators|portatīvais|dators)\s+', '', 'i'
                    ),
                    '\s+(klēpjdators|portatīvais|dators)\s*$', '', 'i'
                )
            ),
            '\s+', ' ', 'g'
        ))
        -- size
        || '|' ||
        CASE
            WHEN display_size IS NULL THEN ''
            WHEN display_size ~ '\d+\.?\d*'
                THEN (regexp_match(display_size, '\d+\.?\d*'))[1]
            ELSE ''
        END,
        ''
    ),
    ''
);

-- 3. Collapse duplicate normalized_key rows. Winner = lowest id; losers deleted.
--    Any laptop_listings pointing at a loser are redirected to the winner.
DO $$
DECLARE
    dup_key TEXT;
    winner_id INT;
    loser_id INT;
BEGIN
    FOR dup_key, winner_id IN (
        SELECT normalized_key, MIN(id)
        FROM laptop_reference
        WHERE normalized_key <> ''
        GROUP BY normalized_key
        HAVING COUNT(*) > 1
    ) LOOP
        UPDATE laptop_listings ll
        SET laptop_reference_id = winner_id
        FROM laptop_reference lr
        WHERE ll.laptop_reference_id = lr.id
          AND lr.id <> winner_id
          AND lr.normalized_key = dup_key;
        FOR loser_id IN (
            SELECT id FROM laptop_reference
            WHERE normalized_key = dup_key AND id <> winner_id
        ) LOOP
            DELETE FROM laptop_reference WHERE id = loser_id;
        END LOOP;
    END LOOP;
END $$;

-- Re-add the UNIQUE constraint.
ALTER TABLE laptop_reference ADD CONSTRAINT laptop_reference_normalized_key_key UNIQUE (normalized_key);

-- 4. Backfill laptop_listings.laptop_reference_id from the re-derived key.
UPDATE laptop_listings ll
SET laptop_reference_id = lr.id
FROM laptop_reference lr
WHERE ll.laptop_reference_id IS NULL
  AND lr.normalized_key <> ''
  AND lr.normalized_key = lower(regexp_replace(trim(COALESCE(ll.brand, '')), '\s+', ' ', 'g')) || '|' ||
                          lower(regexp_replace(
                              trim(
                                  regexp_replace(
                                      regexp_replace(
                                          regexp_replace(trim(COALESCE(ll.model, '')), '\([^)]*\)', '', 'g'),
                                          '^\s*(klēpjdators|portatīvais|dators)\s+', '', 'i'
                                      ),
                                      '\s+(klēpjdators|portatīvais|dators)\s*$', '', 'i'
                                  )
                              ),
                              '\s+', ' ', 'g'
                          )) || '|' ||
                          CASE
                              WHEN ll.display_size IS NULL THEN ''
                              WHEN ll.display_size ~ '\d+\.?\d*'
                                  THEN (regexp_match(ll.display_size, '\d+\.?\d*'))[1]
                              ELSE ''
                          END;

-- 5. Final state (uncomment to inspect after running).
-- SELECT
--   (SELECT COUNT(*) FROM laptop_listings) AS listings,
--   (SELECT COUNT(*) FROM laptop_listings WHERE laptop_reference_id IS NOT NULL) AS listings_with_ref,
--   (SELECT COUNT(*) FROM laptop_reference) AS refs,
--   (SELECT COUNT(*) FROM laptop_reference WHERE normalized_key = '') AS refs_no_key;
