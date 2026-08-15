# Listing Versioning Implementation

## Overview

Implemented automatic versioning for reused ss.com listing IDs. When an ID like `gexxm` is reused for a completely different listing, the system now creates a new version (e.g., `gexxm_v2`, `gexxm_v3`, etc.) instead of overwriting the previous data.

## Problem

ss.com reuses listing IDs after listings expire. For example, `https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html` might first be a "Gaming PC with RTX 3060" and later become "Office PC with i5-10400". Previously, this would overwrite the original listing data.

## Solution

### Core Components

1. **`src/utils/listing_versioning.py`** - New utility module with:
   - `compute_content_fingerprint()` - Creates hash from title, description, price, location
   - `ListingVersionManager` - Handles version detection and management
   - `get_versioned_listing_id()` - Generates versioned IDs (gexxm → gexxm_v2)

2. **Database Schema Changes** - Added `version_number` column to:
   - `listings` table (for GPU/CPU/SSD/RAM listings)
   - `computer_listings` table (for full PC listings)
   - `console_listings` table (for console listings)
   - Removed unique constraint on `listing_id` alone
   - Added unique constraint on `(listing_id, version_number)`

3. **Updated Scraper Repositories**:
   - `src/database/repository.py` - Main `ListingRepository.create_or_update()`
   - `src/database/computer_repository.py` - `ComputerScraper._save_computer_listing()`
   - `src/database/console_repository.py` - `ConsoleRepository.save_listing()`

4. **Updated Models**:
   - `src/models/schemas.py` - Added `version_number: int = 1` to `Listing`, `ConsoleListing`
   - `src/models/computer_schemas.py` - Added `version_number: int = 1` to `ComputerListing`

## How It Works

1. **When scraping a listing:**
   - Extract ss.com ID (e.g., `gexxm`)
   - Compute content fingerprint from title + description + price + location
   - Query database for existing versions of this ID

2. **Version Detection:**
   - **No existing entry** → Create as version 1 (`gexxm`)
   - **Same fingerprint** → Update existing version (same content)
   - **Different fingerprint** → Create new version (`gexxm_v2`, `gexxm_v3`, etc.)

3. **Storage:**
   - Each version stored as separate row with `(listing_id, version_number)` unique
   - Version history tracked in `listing_versions` / `computer_listing_versions` tables

## Example Flow

```
Day 1: Scrape gexxm (Gaming PC RTX 3060)
  → ID: gexxm, version: 1, fingerprint: abc123
  → Action: new

Day 2: Scrape gexxm again (same content)
  → ID: gexxm, version: 1, fingerprint: abc123
  → Action: unchanged

Day 3: gexxm expired, ss.com reused ID for "Office PC i5-10400"
  → ID: gexxm, version: 2, fingerprint: xyz789
  → Action: new_version
  → Original gexxm (v1) preserved

Day 4: Scrape gexxm (same Office PC)
  → ID: gexxm, version: 2, fingerprint: xyz789
  → Action: unchanged
```

## Database Migration

Run the following SQL files in order:

1. `src/database/listing_versioning.sql` - Core versioning schema
2. `src/database/console_schema.sql` - Updated console schema
3. `src/database/computer_schema.sql` - Already had versions, minor updates

Or apply manually:

```sql
-- For listings table
ALTER TABLE listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_listing_id_key;
ALTER TABLE listings ADD CONSTRAINT listings_listing_id_version_unique UNIQUE (listing_id, version_number);

-- For computer_listings table  
ALTER TABLE computer_listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE computer_listings DROP CONSTRAINT IF EXISTS computer_listings_listing_id_key;
ALTER TABLE computer_listings ADD CONSTRAINT computer_listings_listing_id_version_unique UNIQUE (listing_id, version_number);

-- For console_listings table
ALTER TABLE console_listings ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE console_listings DROP CONSTRAINT IF EXISTS console_listings_listing_id_key;
ALTER TABLE console_listings ADD CONSTRAINT console_listings_listing_id_version_unique UNIQUE (listing_id, version_number);
```

## Files Modified

### New Files
- `src/utils/listing_versioning.py` - Versioning utility module
- `src/database/listing_versioning.sql` - Schema migrations

### Modified Files
- `src/models/schemas.py` - Added `version_number` to `Listing`, `ConsoleListing`
- `src/models/computer_schemas.py` - Added `version_number` to `ComputerListing`
- `src/database/repository.py` - Updated `create_or_update()` with versioning
- `src/scraper/computer_scraper.py` - Updated `_save_computer_listing()`
- `src/database/computer_repository.py` - Versioning support
- `src/database/console_repository.py` - New versioning-based `save_listing()`
- `src/database/console_schema.sql` - Complete schema with versioning

## Statistics Tracking

Scrapers now track:
- `new` - Brand new listings (v1)
- `new_version` - New versions of reused IDs (v2, v3, etc.)
- `updated` - Price/content changes to existing version
- `unchanged` - Same content, just refresh last_seen
- `failed` - Failed to scrape

## Backward Compatibility

- All existing listings remain as version 1
- Queries using `listing_id` still work (v1 has no suffix)
- New code uses `get_versioned_listing_id()` when needed
- Version history tables track changes before updates

## Testing

To test the versioning:

1. Scrape a listing, note the ID
2. Manually change the listing content on ss.com (or wait for reuse)
3. Scrape again - should create version 2
4. Check database: `SELECT listing_id, version_number, title FROM listings WHERE listing_id LIKE 'your_id%'`

## Notes

- Versioning is automatic, no manual intervention needed
- Original URLs still reference base ID - version suffix is internal
- Price history is maintained per version
- Re-list detection still works within each version
