# Motherboard and Monitor Scraper Documentation

## Overview
This package adds comprehensive motherboard and monitor scraping capabilities to the SS-Crawler project, including:
- Web scraping for motherboards from ss.com
- Web scraping for monitors from ss.com
- Intelligent model matching with confidence scoring
- Database schema for storing model references
- Flask dashboard integration with visualizations

## File Structure

### New Scraper Files
- `src/scraper/motherboard_scraper.py` - Motherboard scraper implementation
- `src/scraper/monitor_scraper.py` - Monitor scraper implementation

### Database Schema
- `src/database/motherboard_monitor_schema.sql` - SQL schema for motherboard/monitor tables and views

### Import Tools
- `import_motherboard_monitor.py` - Import reference data from Excel files

### CLI Integration
- Updated `src/cli.py` - Added motherboard and monitor CLI commands

### Dashboard Integration (SS-WEBSITE)
- `templates/motherboards.html` - Motherboard listings page with chipset popularity chart
- `templates/monitors.html` - Monitor listings page with statistics
- Updated `templates/base.html` - Navigation menu
- Updated `app.py` - API endpoints for motherboard/monitor data

## Database Schema

### New Tables

#### `motherboard_models`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| brand | VARCHAR(100) | Manufacturer brand |
| model | VARCHAR(200) | Model name |
| socket | VARCHAR(50) | CPU socket type |
| chipset | VARCHAR(100) | Chipset type |
| ram_slots | VARCHAR(50) | Number of RAM slots |
| form_factor | VARCHAR(50) | Form factor (ATX, MicroATX, etc.) |
| search_keywords | TEXT[] | Search keywords for matching |
| normalized_name | VARCHAR(300) | Normalized name for search |

#### `monitor_models`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| brand | VARCHAR(100) | Manufacturer brand |
| model | VARCHAR(200) | Model name |
| size | VARCHAR(20) | Screen size in inches |
| resolution | VARCHAR(50) | Screen resolution |
| refresh_rate | VARCHAR(20) | Refresh rate in Hz |
| panel_type | VARCHAR(50) | Panel type (IPS, VA, TN, OLED) |
| search_keywords | TEXT[] | Search keywords for matching |
| normalized_name | VARCHAR(300) | Normalized name for search |

### New Columns in `listings` Table
- `motherboard_model_id` - Foreign key to motherboard_models
- `motherboard_confidence_score` - Match confidence (0.0-1.0)
- `motherboard_match_method` - Method used for matching
- `monitor_model_id` - Foreign key to monitor_models
- `monitor_confidence_score` - Match confidence (0.0-1.0)
- `monitor_match_method` - Method used for matching

### Database Functions
- `get_motherboard_chipset_stats(p_time_filter)` - Get chipset popularity statistics
- `get_monitor_size_stats(p_time_filter)` - Get monitor size statistics
- `get_monitor_resolution_stats(p_time_filter)` - Get resolution statistics

## CLI Usage

### Scrape Commands

```bash
# Scrape motherboards
python main.py scrape --motherboards --max-pages 5

# Scrape monitors
python main.py scrape --monitors --max-pages 5

# Scrape multiple categories
python main.py scrape --gpu --motherboards --monitors

# Scrape with confidence filter
python main.py scrape --motherboards --confidence 0.8

# Test mode (limit listings)
python main.py scrape --motherboards --test --max-pages 1
```

### Test URL Command

```bash
# Test single motherboard URL
python main.py test-url "https://www.ss.com/.../abc123.html" --motherboards

# Test single monitor URL
python main.py test-url "https://www.ss.com/.../abc123.html" --monitors
```

## Dashboard Features

### Motherboard Page (`/motherboards`)
- Listing table with filters (active only, confidence, time range)
- Chipset popularity doughnut chart
- Model cards with average prices
- Price history tracking
- Matching confidence display

### Monitor Page (`/monitors`)
- Listing table with filters
- Statistics by size
- Statistics by resolution
- Statistics by panel type
- Model cards with specifications
- Price history tracking

### API Endpoints

```
GET /api/motherboards          - Get motherboard listings
GET /api/motherboard-models    - Get aggregated motherboard stats
GET /api/motherboard-chipsets  - Get chipset popularity data
GET /api/monitors              - Get monitor listings
GET /api/monitor-models        - Get aggregated monitor stats
```

## Importing Reference Data

### Prerequisites
- Ensure Motherboards.xlsx and monitors.xlsx exist in the SS-CRAWLER directory
- Run the schema SQL first to create tables

### Import Command
```bash
cd SS-CRAWLER
python import_motherboard_monitor.py
```

This will:
1. Clear existing data from tables
2. Read Excel files
3. Generate search keywords
4. Insert into database

## Matching Algorithm

### Motherboard Matching
The matcher scores listings based on:
- Brand match (30% weight)
- Model match (50% weight)
- Socket mention (10% weight)
- Chipset mention (10% weight)

Match methods:
- `exact` - All fields matched (score >= 0.9)
- `fuzzy` - Major fields matched (score >= 0.7)
- `partial` - Some fields matched

### Monitor Matching
The matcher extracts specifications from text:
- Screen size (e.g., "24", "27.5")
- Resolution (e.g., "1920x1080", "2560x1440", "4K")
- Refresh rate (e.g., "60Hz", "144Hz")
- Panel type (IPS, VA, TN, OLED)

Then scores based on:
- Brand match (25% weight)
- Model match (35% weight)
- Size match (15% weight)
- Resolution match (10% weight)
- Refresh rate match (10% weight)
- Panel type match (5% weight)

## Confidence Levels

- **High (>= 0.9)**: Green badge - Strong match
- **Medium (>= 0.7)**: Yellow badge - Good match
- **Low (< 0.7)**: Red badge - Uncertain match

## Troubleshooting

### Import Issues
```bash
# Check Excel column names
python -c "import pandas as pd; df = pd.read_excel('Motherboards.xlsx'); print(df.columns.tolist())"
```

### Database Schema Issues
```sql
-- Run schema manually
\i src/database/motherboard_monitor_schema.sql
```

### Scraping Issues
- Check network connectivity to ss.com
- Verify category URLs in scraper files
- Review logs in `logs/` directory

## Future Enhancements

1. **Price Alerts**: Notify when specific models drop in price
2. **Market Trends**: Show price trends over time by model
3. **Deal Detection**: Highlight listings priced below market average
4. **Batch Operations**: Match multiple unmatched listings at once
5. **Export Data**: CSV/Excel export of filtered listings

## Support

For issues or questions:
1. Check logs in `logs/scraper_YYYY-MM-DD.log`
2. Verify database connectivity
3. Test single URLs with `test-url` command
4. Review dashboard browser console for JavaScript errors
