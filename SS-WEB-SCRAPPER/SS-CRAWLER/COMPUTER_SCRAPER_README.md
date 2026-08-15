# Computer Scraper for SS-Crawler

This module adds complete PC listing scraping capabilities to SS-Crawler, scraping https://www.ss.com/lv/electronics/computers/pc/ for full computer listings.

## Files Created

### Core Scraper Files
- `src/scraper/computer_parser.py` - Parser for extracting data from computer listings
- `src/scraper/computer_matcher.py` - Matcher for detecting components in listings
- `src/scraper/computer_scraper.py` - Main scraper orchestrator

### Database Files
- `src/database/computer_schema.sql` - Database schema for computer_listings table
- `src/database/computer_repository.py` - Repository for computer listing CRUD operations

### Models
- `src/models/computer_schemas.py` - Pydantic models for computer listings

### Web Dashboard
- `web_app.py` - Flask web application with `/computers` endpoint
- `templates/computers.html` - Dashboard HTML template

### Scripts
- `run_computer_scraper.py` - Standalone script to run the scraper

## Features

### Component Detection
Automatically detects the following components in PC listings:
1. **CPU** - Uses existing CPU matching logic
2. **GPU** - Uses existing GPU matching logic
3. **RAM** - Uses existing RAM matching logic
4. **SSD** - Uses existing SSD matching logic
5. **PSU** - Uses existing PSU matching logic (with fallback)
6. **Case** - Uses existing case matching logic (with fallback)
7. **Monitor** - Uses existing monitor matching logic

### Fallback Rules
- **No PSU mentioned:**
  - If NO GPU detected → assign generic 400W PSU (~€35)
  - If GPU detected → assign generic 650W PSU (~€55)
- **No case mentioned:** assign generic case worth €15
- **No motherboard mentioned:** assign entry-level motherboard based on CPU socket
  - LGA1700: €85, AM5: €120, AM4: €70, etc.

### Filtering Rules (SKIP)
Listings containing these terms are automatically skipped:
- "Pērku" (Buying)
- "Multisistēma Rīga"
- "Jaunaka" (Newest/Store)
- "Veikals" (Store)
- "garantija 2 gadi"
- "Remonts" (Repair)
- "piegādi visā Latvijā" / "piegāde visā Latvijā" (Delivery)

## Usage

### Command Line

```bash
# Scrape computers via main CLI
python main.py scrape --computers --test --max-pages 2

# Or use the standalone script
python run_computer_scraper.py --test --max-pages 2 --limit 10

# Test single URL
python main.py test-url "https://www.ss.com/msg/lv/electronics/computers/pc/abc123.html" --computers
```

### Web Dashboard

```bash
# Start the web server
python web_app.py

# Access the dashboard at:
# http://localhost:5000/computers
```

Dashboard features:
- Listings table with all PC listings
- Click any listing for detailed component breakdown
- Price comparison (listing price vs detected components total)
- Flag listings with comments for debugging
- Search and filter functionality

## Database Schema

The `computer_listings` table stores:
- Basic listing info (id, title, description, price, url, etc.)
- Component matches (cpu_id, gpu_id, ram_id, ssd_id, psu_id, case_id)
- Confidence scores for each component
- Match methods for each component
- Fallback values (psu_wattage, case_price, motherboard_price)
- Calculated totals (components_total, price_difference)
- Flagging system (is_flagged, flag_reason, flag_comment)

## API Endpoints

- `GET /api/computers` - Get all computer listings
- `GET /api/computers/<id>` - Get detailed listing with component breakdown
- `POST /api/computers/<id>/flag` - Flag a listing
- `GET /api/computers/flagged` - Get flagged listings
- `GET /api/computers/search?q=<query>` - Search listings
- `GET /api/computers/stats` - Get statistics
- `GET /api/components` - Get all component references

## Integration with Existing Code

The computer scraper reuses all existing matchers:
- `CPUMatcher` from `cpu_matcher.py`
- `GPUMatcher` from `matcher.py`
- `RAMMatcher` from `ram_matcher.py`
- `SSDMatcher` from `ssd_matcher.py`
- `PSUMatcher` from `psu_matcher.py`
- `CaseMatcher` from `case_matcher.py`

This ensures consistent matching across all scrapers.