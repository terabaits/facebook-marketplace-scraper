-- Migration: split laptop_reference.model into a base name + model number
--
-- Today `laptop_reference.model` mashes the family name and the SKU together
-- ("Vostro 15 5000", "Probook 440 G7", "Aspire 5 A515-58P"). The user
-- wants the family name in `model` ("Vostro 15", "Probook 440", "Aspire 5")
-- and the SKU in a new `model_number` column ("5000", "G7", "A515-58P"). The
-- split is done by a Python script (`backfill_laptop_reference_model_split.py`)
-- because the per-vendor line patterns don't translate cleanly to SQL.
--
-- After this migration:
--   * laptop_reference has a new VARCHAR(64) `model_number` column (NULL-able)
--   * Existing rows keep their current `model` value (no data is touched in
--     this migration); the Python backfill rewrites the rows in a separate
--     runnable step.
--   * The new field shows up in /api/laptops, /api/listing-details, and the
--     staff edit panel in the laptops page spec popup.

ALTER TABLE laptop_reference
    ADD COLUMN IF NOT EXISTS model_number VARCHAR(64);

-- Partial index — used by the staff edit panel for unique-lookups and the
-- (future) "model number search" feature. Cheap to maintain since most
-- rows will be NULL for a while.
CREATE INDEX IF NOT EXISTS idx_laptop_reference_model_number
    ON laptop_reference (model_number)
    WHERE model_number IS NOT NULL;
