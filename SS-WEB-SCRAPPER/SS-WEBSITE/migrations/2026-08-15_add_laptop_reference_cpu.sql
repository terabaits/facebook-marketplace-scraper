-- Migration: add laptop_reference_cpu table and link laptop_listings to it.
--
-- Same pattern as `laptop_reference` for the brand+model+size, but for CPU.
-- The CPU name is messy: ss.com often drops the brand prefix ("I5", "I7"), the
-- casing is inconsistent ("i5-1135g7" vs "I5-1135G7"), and there is trademark
-- noise ("Intel(R) Core(TM) i7"). The new table stores the *canonical* model
-- (e.g. "i7-11400H", "Ryzen 7 5800H", "M2") and the FK column on
-- laptop_listings points at it. The scraper uses `CPUReferenceResolver` to
-- create rows on miss; legacy rows are backfilled separately by
-- `backfill_laptop_reference_cpu.py`.
--
-- After this migration:
--   * laptop_listings.cpu_reference_id is an indexed INT (no DB-level FK
--     constraint; the scraper is the only writer)
--   * laptop_reference_cpu.normalized_key is the case-insensitive
--     "{brand}|{model}" key (e.g. "intel|i7-11400h") and is UNIQUE
--   * rows where the raw CPU is empty / unparseable ("Intel", "Processor")
--     stay with cpu_reference_id = NULL

-- 1. Create the reference table.
CREATE TABLE IF NOT EXISTS laptop_reference_cpu (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(64) NOT NULL,                    -- Intel / AMD / Apple / Qualcomm
    model VARCHAR(128) NOT NULL,                   -- canonical model (e.g. "i7-11400H")
    normalized_key VARCHAR(256) NOT NULL UNIQUE,   -- lower(brand) | lower(model)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_laptop_reference_cpu_key
    ON laptop_reference_cpu (normalized_key);

-- 2. Add the FK column on laptop_listings.
ALTER TABLE laptop_listings
    ADD COLUMN IF NOT EXISTS cpu_reference_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_laptop_listings_cpu_reference_id
    ON laptop_listings (cpu_reference_id)
    WHERE cpu_reference_id IS NOT NULL;

-- 3. Backfill happens in Python via `backfill_laptop_reference_cpu.py`
--    because the normalization rules live in `src/scraper/cpu_reference_resolver.py`
--    (multi-vendor, case-folding, suffix handling, etc.) and are too complex
--    for a one-shot SQL CASE/REGEXP.
--
--    Run from SS-CRAWLER root, with venv active:
--        python backfill_laptop_reference_cpu.py --dry-run   # preview
--        python backfill_laptop_reference_cpu.py             # apply

-- 4. Final state (uncomment to inspect after running).
-- SELECT
--   (SELECT COUNT(*) FROM laptop_listings) AS listings,
--   (SELECT COUNT(*) FROM laptop_listings WHERE cpu_reference_id IS NOT NULL) AS listings_with_cpu_ref,
--   (SELECT COUNT(*) FROM laptop_reference_cpu) AS cpu_refs;
