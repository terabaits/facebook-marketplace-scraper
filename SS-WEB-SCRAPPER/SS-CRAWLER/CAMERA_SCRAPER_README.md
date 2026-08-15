# Camera Scraper for SS-CRAWLER

This document describes the camera scraper implementation for the SS-CRAWLER project.

## Overview

The camera scraper fetches camera body listings from ss.com (specifically from `/lv/electronics/photo-optics/slr-cameras/`), matches them to the camera reference database, and stores the results with lens detection capability.

## Filtering Rules

The scraper automatically filters out listings containing:
- "nikon" (case insensitive)
- "Jauns ar 2 gadu garantiju" (new with 2 year warranty)
- Online stores ("internetveikals")
- New items ("jauns")

## Files Created

### 1. Database Schema
- **File:** `src/database/camera_schema.sql`
- Contains:
  - `camera_reference` table for storing camera reference data
  - Indexes for efficient lookups
  - View `camera_listings_view` for easy querying
  - Functions for brand and model statistics
  - `listing_flags` table for debugging/moderation

### 2. Database Import Script
- **File:** `import_cameras.py`
- Imports camera data from `All_Cameras_Codecs_Fixed.xlsx`
- Usage: `python import_cameras.py [optional_excel_path]`

### 3. Schema Application
- **File:** `apply_camera_schema.py`
- Applies the camera schema to PostgreSQL
- Usage: `python apply_camera_schema.py`

### 4. Camera Matcher
- **File:** `src/scraper/camera_matcher.py`
- Implements camera matching logic
- Features:
  - Brand detection (Canon, Sony, Fujifilm, Panasonic, Blackmagic, Hasselblad, etc.)
  - Model matching with confidence scoring
  - Keyword-based matching using camera specs
  - Support for partial model matches

### 5. Camera Scraper
- **File:** `src/scraper/camera_scraper.py`
- Main scraper class
- Features:
  - Category page scraping with pagination
  - Camera body matching using reference database
  - Lens detection in listings (using existing lens matcher)
  - Price and location extraction
  - Content-based duplicate detection
  - Database integration

### 6. Database Repository Updates
- **File:** `src/database/repository.py`
- Added `CameraRepository` class
- Updated `ListingRepository` to handle camera listings

### 7. Schema Updates
- **File:** `src/models/schemas.py`
- Added `CameraReference` model
- Added `CameraMatchResult` model
- Added camera fields to `Listing` model

### 8. CLI Integration
- **File:** `src/cli.py`
- Added `--cameras` flag for scrape command
- Added `cameras` option for test-url command
- Added `_scrape_cameras()` function
- Added `_test_url_camera()` function

### 9. Web Dashboard
- **File:** `templates/cameras.html`
- Camera listings dashboard at `/cameras`
- Features:
  - Statistics display (total, active, matched, avg price)
  - Brand and model breakdown
  - Lens statistics integration
  - Search and filter functionality
  - Custom SVG camera icons for each brand
  - Flagging system for debugging

### 10. Web API Endpoints
- **File:** `web_app.py`
- Added to existing Flask app:
  - `/cameras` - Camera listings page
  - `/api/cameras` - List cameras
  - `/api/cameras/stats` - Camera statistics
  - `/api/cameras/<id>` - Camera detail
  - `/api/cameras/<id>/flag` - Flag listing
  - `/api/cameras/flagged` - Get flagged cameras
  - `/api/cameras/search` - Search cameras
  - `/api/lenses/stats` - Lens statistics for camera page

## Database Schema

### camera_reference Table
```sql
- id (SERIAL PRIMARY KEY)
- brand (VARCHAR) - Camera manufacturer
- model (VARCHAR) - Model name
- model_original (VARCHAR) - Original model name
- mount (VARCHAR) - Lens mount type
- sensor (VARCHAR) - Sensor type/size
- camera_type (VARCHAR) - Mirrorless, DSLR, etc.
- category (VARCHAR) - Pro, Consumer, etc.
- release_year (INTEGER)
- resolution (VARCHAR) - Megapixels
- fps (VARCHAR) - Frames per second
- iso (VARCHAR) - ISO range
- focus_points (VARCHAR)
- video_specs (TEXT)
- battery (VARCHAR)
- storage (VARCHAR)
- screen (VARCHAR)
- evf (VARCHAR)
- has_raw (BOOLEAN)
- has_clog, has_clog2, has_clog3 (BOOLEAN) - Canon Log
- has_slog, has_slog2, has_slog3 (BOOLEAN) - Sony Log
- has_4k, has_8k (BOOLEAN)
- sd_type (VARCHAR)
- search_keywords (TEXT[])
- normalized_name (VARCHAR)
```

### listing_flags Table
```sql
- id (SERIAL PRIMARY KEY)
- listing_id (VARCHAR) -> listings(listing_id)
- flag_type (VARCHAR) - incorrect_match, missing_info, spam, other
- comment (TEXT)
- created_at (TIMESTAMP)
- resolved (BOOLEAN)
- resolved_at (TIMESTAMP)
- resolved_by (VARCHAR)
```

## Usage

### Import Camera Reference Data
```bash
python import_cameras.py
```

### Apply Database Schema
```bash
python apply_camera_schema.py
```

### Run Camera Scraper
```bash
# Scrape cameras
python -m src.cli scrape --cameras

# Scrape with options
python -m src.cli scrape --cameras --max-pages 5 --limit 50

# Test single URL
python -m src.cli test-url "https://www.ss.com/.../msg/.../ID.html" --cameras
```

### Start Web Dashboard
```bash
python web_app.py
# Access at http://localhost:5000/cameras
```

## Matching Algorithm

The camera matcher uses a scoring system:

1. **Brand Detection** (0.35 points)
   - Detects brand from text
   - Prefers exact brand matches

2. **Model Matching** (0.50 points)
   - Exact model name match
   - Partial model matching for model parts

3. **Normalized Name** (0.35 points)
   - Checks normalized camera name

4. **Keywords** (0.20 points)
   - Searches against camera search_keywords

5. **Mount Detection** (0.10 points)
   - Bonus for mount mention in listing

6. **Sensor Type** (0.05 points)
   - Bonus for sensor mention

Minimum threshold: 0.5 (50%) confidence to accept a match

## Lens Detection

The scraper also detects lenses mentioned in camera listings:
- Uses existing lens reference data
- Matches brand, focal length, and model keywords
- Stores top 3 lens matches in listing description
- Displays lens badge on dashboard when detected

## Custom Icons

The dashboard displays custom SVG icons for each camera brand:
- Canon (red)
- Sony (blue)
- Fujifilm (orange)
- Panasonic/Lumix (green)
- Blackmagic (purple)
- Hasselblad (yellow)
- Generic camera (gray)

## Statistics Available

### Camera Body Statistics
- Total listings
- Active listings
- Matched listings
- Average, min, max prices
- Breakdown by brand
- Breakdown by model
- Price trends

### Lens Statistics (integrated)
- Total lens listings
- Average lens price
- Price range
- Breakdown by lens brand

## Flagging System

For debugging scraper errors:
- Flag listing with type: incorrect_match, missing_info, spam, other
- Add comments for context
- View flagged listings separately
- Resolve flags when fixed

## Configuration

The scraper uses the same configuration system as other scrapers:
- Database settings from `config.yaml`
- Scraper settings (max_pages, max_listings, etc.)
- Confidence thresholds (default 50% for cameras)

## Notes

- Camera listings are filtered to exclude Nikon (per requirements)
- The scraper integrates with existing lens matching logic
- All listings are stored with confidence scores
- Inactive listings are tracked but marked as such
- Duplicate detection uses content hashing
