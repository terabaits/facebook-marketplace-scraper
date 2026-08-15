-- Migration: laptop_reference feature flags
--
-- Today the laptop_reference row only stores material, USB-C / USB / HDMI
-- counts, and resolution. The admin edit panel needs four more yes/no
-- feature flags (HDMI presence, USB-C with DisplayPort+PD, Ethernet, Touchscreen)
-- and a refresh-rate number (Hz). The user is also replacing the HDMI count
-- input (always 0 or 1 in practice) with a yes/no toggle.
--
-- After this migration:
--   * laptop_reference has new columns: has_hdmi, has_video_pd_usb_c, has_ethernet,
--     has_touchscreen, refresh_rate_hz
--   * hdmi_count is left in place for backward compat (any non-zero becomes
--     has_hdmi=true on backfill)
--   * Existing rows get NULL for all new flags — staff can fill in via the
--     edit panel, or the scraper can pre-populate has_touchscreen / refresh_rate_hz
--     from the listing description

ALTER TABLE laptop_reference
    ADD COLUMN IF NOT EXISTS has_hdmi BOOLEAN,
    ADD COLUMN IF NOT EXISTS has_video_pd_usb_c BOOLEAN,
    ADD COLUMN IF NOT EXISTS has_ethernet BOOLEAN,
    ADD COLUMN IF NOT EXISTS has_touchscreen BOOLEAN,
    ADD COLUMN IF NOT EXISTS refresh_rate_hz SMALLINT
        CHECK (refresh_rate_hz IS NULL OR (refresh_rate_hz BETWEEN 30 AND 1000));

-- Backfill has_hdmi from the legacy hdmi_count column (non-zero -> true).
UPDATE laptop_reference
SET has_hdmi = CASE WHEN COALESCE(hdmi_count, 0) > 0 THEN TRUE ELSE FALSE END
WHERE has_hdmi IS NULL AND hdmi_count IS NOT NULL;

-- Helpful partial indexes for the new filter dropdowns (mostly NULL today,
-- but cheap to maintain and will speed up "listings with Ethernet" once
-- staff fill in the data).
CREATE INDEX IF NOT EXISTS idx_laptop_reference_refresh_rate
    ON laptop_reference (refresh_rate_hz)
    WHERE refresh_rate_hz IS NOT NULL;

-- Note: the user removed the material CHECK constraint later, see next
-- migration if you also want to allow 'Unknown' as a value. We keep the
-- original check ('Plastic' / 'Metal') for now.
