"""SSD Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from src.database.repository import DatabaseRepository
from src.database.connection import DatabaseConnection
from src.models.schemas import Listing, SSDReference
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.ssd_parser import SSDParser
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import ScraperConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash, extract_ssd_tokens

logger = get_logger("ssd_scraper")


class SSDScraper:
    """Scraper for SSD listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/computers/completing-pc/ssd/"
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize the SSD scraper."""
        self.config = config or ScraperConfig()
        self.crawler = Crawler(self.config)
        self.parser = SSDParser()
        
        # Initialize database
        db_conn = DatabaseConnection(
            host=self.config.database.host,
            port=self.config.database.port,
            database=self.config.database.database,
            user=self.config.database.user,
            password=self.config.database.password
        )
        self.repo = DatabaseRepository(db_conn)
        
        # Initialize matcher (will be loaded on first use)
        self.matcher: Optional[SSDMatcher] = None
        self.seen_urls: Set[str] = set()
        
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0
        }
    
    def _load_ssd_references(self) -> List[SSDReference]:
        """Load SSD references from database."""
        try:
            with self.repo.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, brand, model, interface, form_factor, 
                           capacity_gb, controller, configuration, has_dram, hmb,
                           nand_brand, nand_type, layers, read_speed_mb, write_speed_mb,
                           category, notes, search_keywords, normalized_name
                    FROM ssd_reference
                    ORDER BY brand, model
                """)
                
                ssd_list = []
                for row in cursor.fetchall():
                    ssd = SSDReference(
                        id=row[0],
                        brand=row[1],
                        model=row[2],
                        interface=row[3],
                        form_factor=row[4],
                        capacity_gb=row[5],
                        controller=row[6],
                        configuration=row[7],
                        has_dram=row[8],
                        hmb=row[9],
                        nand_brand=row[10],
                        nand_type=row[11],
                        layers=row[12],
                        read_speed_mb=row[13],
                        write_speed_mb=row[14],
                        category=row[15],
                        notes=row[16],
                        search_keywords=row[17] if row[17] else [],
                        normalized_name=row[18]
                    )
                    ssd_list.append(ssd)
                
                logger.info(f"Loaded {len(ssd_list)} SSD references from database")
                return ssd_list
                
        except Exception as e:
            logger.error(f"Failed to load SSD references: {e}")
            return []
    
    def _ensure_matcher_loaded(self):
        """Ensure the matcher is loaded."""
        if self.matcher is None:
            ssd_list = self._load_ssd_references()
            self.matcher = SSDMatcher(ssd_list)
    
    def _extract_location(self, html: str) -> Optional[str]:
        """Extract seller location from HTML."""
        # Look for location in the page
        soup_match = re.search(r'<td[^>]*>\s*<b>([^<]+)</b>\s*</td>\s*<td[^>]*class="td_address"[^>]*>([^<]+)</td>', html)
        if soup_match:
            return soup_match.group(2).strip()
        
        # Alternative pattern
        loc_match = re.search(r'class="td_address"[^>]*>([^<]+)</td>', html)
        if loc_match:
            return loc_match.group(1).strip()
        
        return None
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """
        Scrape a single SSD listing.
        
        Args:
            listing_id: The listing ID
            url: Full URL to the listing
            
        Returns:
            Listing object if successful
        """
        self._ensure_matcher_loaded()
        
        try:
            # Fetch the page
            result = self.crawler.fetch(url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.warning(f"Failed to fetch {url}: {result.error_msg}")
                self.stats['failed'] += 1
                return None
            
            # Parse the listing
            listing = self.parser.parse_listing_page(result.html, listing_id, url)
            
            if not listing:
                logger.warning(f"Failed to parse listing {listing_id}")
                self.stats['failed'] += 1
                return None
            
            # Extract location
            location = self._extract_location(result.html)
            if location:
                listing.seller_location = location
            
            # Match to SSD reference
            match_result = self.matcher.match_listing(
                listing.title,
                listing.capacity_gb
            )
            
            if match_result.ssd:
                listing.matched_ssd_id = match_result.ssd.id
                listing.ssd_confidence_score = match_result.confidence
                listing.ssd_match_method = match_result.method
                self.stats['matched'] += 1
                logger.info(f"Matched {listing_id}: {match_result.ssd.brand} {match_result.ssd.model} "
                           f"({match_result.confidence:.0%} confidence)")
            else:
                logger.info(f"No match for {listing_id}: {listing.title[:50]}")
            
            # Compute content hash
            listing.content_hash = compute_content_hash(
                listing.title,
                listing.price_eur,
                listing.seller_location or ""
            )
            
            return listing
            
        except Exception as e:
            logger.error(f"Error scraping listing {listing_id}: {e}")
            self.stats['failed'] += 1
            return None
    
    def scrape_category(self, max_pages: int = 0, limit: int = 0) -> List[Listing]:
        """
        Scrape all SSD listings from the category.
        
        Args:
            max_pages: Maximum pages to scrape (0 = unlimited)
            limit: Maximum listings to process (0 = unlimited)
            
        Returns:
            List of scraped listings
        """
        self._ensure_matcher_loaded()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page = 1
        total_listings = 0
        
        logger.info(f"Starting SSD scraper from {current_url}")
        
        while True:
            # Check page limit
            if max_pages > 0 and page > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break
            
            logger.info(f"Fetching page {page}: {current_url}")
            
            # Fetch category page
            result = self.crawler.fetch(current_url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.error(f"Failed to fetch page {page}: {result.error_msg}")
                break
            
            # Extract listing URLs
            listing_urls = self.parser.extract_listing_urls(result.html, self.BASE_URL)
            
            logger.info(f"Found {len(listing_urls)} listings on page {page}")
            
            for listing_id, url in listing_urls:
                # Check global limit
                if limit > 0 and total_listings >= limit:
                    logger.info(f"Reached global limit ({limit})")
                    return listings
                
                # Skip if already seen
                if listing_id in self.seen_urls:
                    continue
                self.seen_urls.add(listing_id)
                
                # Scrape individual listing
                listing = self.scrape_listing(listing_id, url)
                
                if listing:
                    # Save to database
                    self._save_listing(listing)
                    listings.append(listing)
                    total_listings += 1
                
                self.stats['processed'] += 1
            
            # Check for next page
            pagination = self.parser.extract_pagination_info(result.html)
            if not pagination['has_next']:
                logger.info("No more pages")
                break
            
            current_url = pagination['next_url']
            if not current_url.startswith('http'):
                current_url = f"{self.BASE_URL}{current_url}"
            
            page += 1
        
        logger.info(f"SSD scraping complete. Stats: {self.stats}")
        return listings
    
    def _save_listing(self, listing: Listing):
        """Save listing to database."""
        try:
            # Check if listing exists
            existing = self.repo.get_listing_by_id(listing.listing_id)
            
            if existing:
                # Check if changed
                if existing.content_hash == listing.content_hash:
                    # Just update last_seen
                    self.repo.update_listing_last_seen(listing.listing_id)
                    self.stats['unchanged'] += 1
                else:
                    # Update with new data
                    self.repo.update_listing(listing)
                    self.stats['updated'] += 1
            else:
                # Insert new
                self.repo.insert_listing(listing)
                self.stats['new'] += 1
                
        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")
    
    def scrape_single(self, url: str) -> Optional[Listing]:
        """
        Scrape a single SSD listing by URL.
        
        Args:
            url: The listing URL
            
        Returns:
            Listing object if successful
        """
        # Extract listing ID from URL
        match = re.search(r'/([a-z]+)\.html$', url)
        if not match:
            logger.error(f"Could not extract listing ID from URL: {url}")
            return None
        
        listing_id = match.group(1)
        return self.scrape_listing(listing_id, url)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return self.stats.copy()
