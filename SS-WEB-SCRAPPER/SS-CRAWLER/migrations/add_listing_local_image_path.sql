-- Migration: Add local_image_path column to listings table
-- Run this SQL in PostgreSQL to enable persisting local downloaded image paths.

ALTER TABLE listings ADD COLUMN IF NOT EXISTS local_image_path TEXT;

-- Index for quickly finding listings without local images (used by backfill utilities).
CREATE INDEX IF NOT EXISTS idx_listings_local_image_path ON listings(local_image_path) WHERE local_image_path IS NULL;

-- Verify the column was added.
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'listings'
  AND column_name = 'local_image_path';
