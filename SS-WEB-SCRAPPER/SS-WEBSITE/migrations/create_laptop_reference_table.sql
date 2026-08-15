-- Laptop reference table: canonical per-model data, editable by staff (mod/admin)
-- from the laptops page detail popup. laptop_listings rows join to this table
-- through normalized_key, so one edit shows up on every listing with the same
-- brand+model+size (case-insensitive).
--
-- is_valid ("VALID") is the admin-only mark for the canonical/good version of a
-- model. It will be used as the comparison target when duplicate laptop models
-- are merged.

CREATE TABLE IF NOT EXISTS laptop_reference (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(128) NOT NULL,
    model VARCHAR(255) NOT NULL,
    -- The SKU/identifier that distinguishes specific configurations of the
    -- same family (e.g. "A515-58P" for Aspire 5, "G7" for ProBook 440 G7).
    -- Populated by the staff edit panel and the model-split backfill.
    model_number VARCHAR(64),
    display_size VARCHAR(16),
    -- lower(trim(brand)) | lower(trim(model)) | display size digits only.
    -- Whitespace-collapsed; case-insensitive so 'Macbook Air' = 'Macbook air'.
    normalized_key VARCHAR(512) NOT NULL UNIQUE,
    material VARCHAR(16) CHECK (material IN ('Plastic', 'Metal')),
    usb_c_count INTEGER CHECK (usb_c_count BETWEEN 0 AND 20),
    usb_count INTEGER CHECK (usb_count BETWEEN 0 AND 20),
    -- Legacy HDMI count, kept for back-compat. New code should read has_hdmi.
    hdmi_count INTEGER CHECK (hdmi_count BETWEEN 0 AND 20),
    -- Yes/no feature flags (added 2026-08-15; see 2026-08-15_laptop_reference_feature_flags.sql)
    has_hdmi BOOLEAN,
    has_video_pd_usb_c BOOLEAN,
    has_ethernet BOOLEAN,
    has_touchscreen BOOLEAN,
    refresh_rate_hz SMALLINT CHECK (refresh_rate_hz IS NULL OR (refresh_rate_hz BETWEEN 30 AND 1000)),
    resolution VARCHAR(32),
    is_valid BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_laptop_reference_key ON laptop_reference (normalized_key);

-- Populate from existing listings. Idempotent (ON CONFLICT DO NOTHING).
-- Rows are inserted most-frequent variant first, so the most common casing of a
-- model wins the normalized_key conflict and becomes the display name.
-- resolution is pre-filled with the most frequent NNNNxNNNN pattern found in the
-- group's listing descriptions (best effort; staff can correct it).
INSERT INTO laptop_reference (brand, model, display_size, normalized_key, resolution)
SELECT
    d.brand,
    d.model,
    d.display_size,
    lower(regexp_replace(trim(d.brand), '\s+', ' ', 'g')) || '|' ||
    lower(regexp_replace(trim(d.model), '\s+', ' ', 'g')) || '|' ||
    regexp_replace(COALESCE(d.display_size, ''), '[^0-9.]', '', 'g') AS normalized_key,
    res.resolution
FROM (
    SELECT brand, model, display_size, COUNT(*) AS cnt
    FROM laptop_listings
    WHERE brand IS NOT NULL AND model IS NOT NULL
    GROUP BY brand, model, display_size
) d
LEFT JOIN LATERAL (
    SELECT (m[1] || 'x' || m[2]) AS resolution
    FROM (
        SELECT regexp_match(ll.description, '(\d{3,4})\s*[x×]\s*(\d{3,4})', 'i') AS m
        FROM laptop_listings ll
        WHERE ll.brand = d.brand
          AND ll.model = d.model
          AND ll.display_size IS NOT DISTINCT FROM d.display_size
          AND ll.description ~* '\d{3,4}\s*[x×]\s*\d{3,4}'
    ) matches
    WHERE m IS NOT NULL
    GROUP BY m
    ORDER BY COUNT(*) DESC
    LIMIT 1
) res ON true
ORDER BY d.cnt DESC
ON CONFLICT (normalized_key) DO NOTHING;
