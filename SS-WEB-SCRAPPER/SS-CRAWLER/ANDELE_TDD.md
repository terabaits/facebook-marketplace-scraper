# Andele Mandele Scraper - Technical Design Document (TDD)

## Overview
A modular scraper for andelemandele.lv that integrates with the existing SS-Crawler infrastructure without breaking existing functionality.

## Architecture Principles
1. **Modularity**: Separate scraper module that reuses existing matching algorithms
2. **Backward Compatibility**: No modifications to existing tables or ss.com scraping
3. **Code Reuse**: Leverage existing matchers (GPU, CPU, SSD, RAM, PSU, Monitor, Motherboard)
4. **Extensibility**: Easy to add new marketplace sources

## Project Structure

```
SS-CRAWLER/
├── src/
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── engine.py                 # Existing SS scraper
│   │   ├── andele_scraper.py         # NEW: Andele scraper
│   │   ├── cpu_scraper.py            # Existing
│   │   ├── ssd_scraper.py            # Existing
│   │   └── ...                       # Other existing scrapers
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── ss_listing_parser.py      # Existing SS parser
│   │   └── andele_parser.py          # NEW: Andele-specific parser
│   ├── matchers/                     # Existing matchers (REUSED)
│   │   ├── __init__.py
│   │   ├── gpu_matcher.py
│   │   ├── cpu_matcher.py
│   │   ├── ssd_matcher.py
│   │   ├── ram_matcher.py
│   │   ├── psu_matcher.py
│   │   ├── monitor_matcher.py
│   │   └── motherboard_matcher.py
│   └── cli.py                        # MODIFIED: Add --andele flag
└── main.py                           # Entry point (no changes needed)
```

## New Files to Create

### 1. `src/parsers/andele_parser.py`
**Purpose**: Extract data from Andele HTML structure

**Key Differences from SS Parser**:
- Andele uses different HTML structure (div-based vs table-based)
- Different URL pattern: `/perle/[ID]/[slug]/`
- Different pagination: JavaScript-based or URL parameters
- Price format may differ

**Class Structure**:
```python
class AndeleParser:
    def parse_listing(self, html: str, url: str) -> ListingData:
        """Extract listing data from Andele HTML"""
        
    def parse_list_page(self, html: str) -> Tuple[List[str], Optional[str]]:
        """Extract listing URLs and next page URL from category page"""
        
    def extract_price(self, html: BeautifulSoup) -> Optional[float]:
        """Extract and normalize price"""
        
    def extract_title(self, html: BeautifulSoup) -> str:
        """Extract listing title"""
        
    def extract_description(self, html: BeautifulSoup) -> Optional[str]:
        """Extract listing description"""
        
    def extract_location(self, html: BeautifulSoup) -> Optional[str]:
        """Extract seller location"""
        
    def extract_images(self, html: BeautifulSoup) -> List[str]:
        """Extract image URLs"""
```

### 2. `src/scraper/andele_scraper.py`
**Purpose**: Main scraper class for Andele marketplace

**Class Structure**:
```python
class AndeleScraper:
    def __init__(self, config: AppConfig, db_session):
        self.config = config
        self.db = db_session
        self.parser = AndeleParser()
        self.matchers = {
            'gpu': GPUMatcher(),
            'cpu': CPUMatcher(),
            'ssd': SSDMatcher(),
            'ram': RAMMatcher(),
            'psu': PSUMatcher(),
            'monitor': MonitorMatcher(),
            'motherboard': MotherboardMatcher(),
        }
        
    def scrape_category(self, category: str, max_pages: int = 0) -> ScrapeResult:
        """Scrape specific category (gpu, cpu, ssd, etc.)"""
        
    def scrape_listing(self, url: str) -> Optional[ListingData]:
        """Scrape single listing"""
        
    def process_listing(self, data: ListingData) -> ProcessedListing:
        """Apply matchers and save to database"""
        
    def get_category_url(self, category: str) -> str:
        """Map category to Andele URL"""
        urls = {
            'gpu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:409',
            'cpu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:405',
            'ssd': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:404',
            'ram': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:406',
            'psu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:415',
            'computer': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:413',
            'monitor': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:578',
            'motherboard': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:403',
        }
        return urls.get(category)
```

### 3. CLI Integration
**File**: `src/cli.py`

**Add to Argument Parser**:
```python
# In create_parser():
scrape_parser.add_argument(
    "--andele",
    action="store_true",
    help="Use Andele Mandele scraper instead of SS.com"
)

# Category-specific flags
scrape_parser.add_argument(
    "--andele-gpu",
    action="store_true",
    help="Scrape GPU from Andele"
)
# ... etc for each category

# Test URL support
test_parser.add_argument(
    "--andele",
    action="store_true",
    help="Parse as Andele listing"
)
```

## Command-Line Interface

### New Commands

```bash
# Scrape from Andele (specific categories)
python main.py scrape --andele --gpu
python main.py scrape --andele --cpu
python main.py scrape --andele --ssd
python main.py scrape --andele --ram
python main.py scrape --andele --psu
python main.py scrape --andele --monitor
python main.py scrape --andele --motherboard
python main.py scrape --andele --computer

# Scrape multiple categories
python main.py scrape --andele --gpu --cpu --ssd

# Scrape all from Andele
python main.py scrape --andele --all

# Test single URL from Andele
python main.py test-url "https://www.andelemandele.lv/perle/15757706/dell-wd19-dokstacija-ar-ladetaju-130-w-usb-c-4k/" --andele --gpu

# With options
python main.py scrape --andele --gpu --max-pages 5 --limit 100
python main.py scrape --andele --gpu --dry-run  # Parse only, don't save
```

## Database Integration

### Existing Tables Used (No Changes)
- `listings` - Store scraped listings
- `gpu_reference` - GPU matching reference
- `cpu_reference` - CPU matching reference
- `ssd_reference` - SSD matching reference
- `ram_reference` - RAM matching reference
- `psu_reference` - PSU matching reference
- `monitor_reference` - Monitor matching reference
- `motherboard_reference` - Motherboard matching reference
- `price_history` - Track price changes

### New Column (Optional)
Add `source` column to listings table to distinguish between ss.com and andelemandele:
```sql
ALTER TABLE listings ADD COLUMN source VARCHAR(50) DEFAULT 'ss.com';
-- or use existing category field with prefix: 'andele_gpu'
```

## HTML Structure Analysis

### Andele Listing Page
From the example URL: `https://www.andelemandele.lv/perle/15757706/dell-wd19-dokstacija-ar-ladetaju-130-w-usb-c-4k/`

**Key Elements to Extract**:
1. **Title**: Usually in `<h1>` or specific header class
2. **Price**: Look for price element (may need JavaScript rendering)
3. **Description**: In description div
4. **Images**: Gallery images
5. **Location**: Seller location
6. **Date**: Posted date

### Category Pages
URLs use hash-based filters: `#order:actual/attributes:409`

**Challenge**: Andele may use JavaScript/AJAX loading - may need:
- Selenium/Playwright for JS-rendered content
- Or API endpoints if available
- Headless browser for pagination

## Implementation Steps

### Phase 1: Parser Implementation (Week 1)
1. ✅ Create `src/parsers/andele_parser.py`
2. ✅ Implement HTML parsing for listing pages
3. ✅ Implement category page parsing
4. ✅ Handle JavaScript rendering (if needed)
5. ✅ Test parser with sample URLs

### Phase 2: Scraper Implementation (Week 1-2)
1. ✅ Create `src/scraper/andele_scraper.py`
2. ✅ Integrate existing matchers
3. ✅ Implement category scraping
4. ✅ Handle pagination
5. ✅ Error handling and retries
6. ✅ Rate limiting

### Phase 3: CLI Integration (Week 2)
1. ✅ Modify `src/cli.py` to add --andele flags
2. ✅ Update argument parsing
3. ✅ Integrate AndeleScraper into command dispatch
4. ✅ Test all CLI commands

### Phase 4: Testing & Validation (Week 2-3)
1. ✅ Test with single URL
2. ✅ Test category scraping
3. ✅ Verify data matches existing tables
4. ✅ Test matchers with Andele data
5. ✅ Performance testing

### Phase 5: Documentation (Week 3)
1. ✅ Update README.md
2. ✅ Add usage examples
3. ✅ Document any differences from SS scraper

## Technical Challenges & Solutions

### Challenge 1: JavaScript Rendering
**Problem**: Andele may load content dynamically
**Solutions**:
- Option A: Use Selenium/Playwright (slower, more resource intensive)
- Option B: Find API endpoints (faster, preferred)
- Option C: Use requests-html with JS rendering

**Recommendation**: Start with Option B (API), fallback to Option C

### Challenge 2: Different HTML Structure
**Problem**: Andele uses different CSS classes/structure than SS
**Solution**: Create separate parser with its own selectors

### Challenge 3: Price Format Differences
**Problem**: Andele may format prices differently
**Solution**: Flexible price extraction with multiple fallback patterns

### Challenge 4: URL Pattern Differences
**Problem**: Different URL structure for listings
**Solution**: Separate URL handling in parser

### Challenge 5: Session/Cookies
**Problem**: Andele may require session handling
**Solution**: requests.Session() with proper headers

## Testing Strategy

### Unit Tests
- Test parser with sample HTML files
- Test each extraction method
- Test URL builders

### Integration Tests
- Test full scrape flow
- Test database integration
- Test matchers with Andele data

### Manual Tests
```bash
# Test single URL
python main.py test-url "https://www.andelemandele.lv/perle/15757706/..." --andele --gpu

# Test category (1 page)
python main.py scrape --andele --gpu --max-pages 1 --dry-run

# Test save
python main.py scrape --andele --gpu --max-pages 1
```

## Success Criteria

1. ✅ Can scrape all categories (GPU, CPU, SSD, RAM, PSU, Monitor, Motherboard, Computer)
2. ✅ Data correctly matched to existing reference tables
3. ✅ No breaking changes to existing SS scraper
4. ✅ CLI works with --andele flag
5. ✅ Test URL command works for Andele
6. ✅ Data quality comparable to SS scraper
7. ✅ Rate limiting to avoid being blocked

## Future Enhancements

1. Parallel scraping
2. Automatic marketplace detection from URL
3. More marketplaces (Amazon, 1a.lv, etc.)
4. Unified dashboard showing all sources

## Notes

- Reuse existing matchers - they handle the complex matching logic
- Keep parser simple - just extract raw data
- Use same database schema - no migrations needed
- Consider adding source tracking for analytics
