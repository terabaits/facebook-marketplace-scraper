"""SSD Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, SSDReferenceRepository, ScrapeRunRepository
from src.models.schemas import Listing, SSDReference
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.ssd_parser import SSDParser
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import AppConfig, ScraperConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash

logger = get_logger("ssd_scraper")


class SSDScraper:
    """Scraper for SSD listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/computers/completing-pc/ssd/"
    
    def __init__(self, config: AppConfig):
        """Initialize the SSD scraper."""
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.parser = SSDParser()
        self.matcher: Optional[SSDMatcher] = None
        
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0
        }
    
    def initialize(self):
        """Initialize database and load SSD references."""
        logger.info("Initializing SSD scraper...")
        
        # Initialize database
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load SSD reference data
        with get_session() as session:
            ssds = SSDReferenceRepository.get_all(session)
            self.matcher = SSDMatcher(ssds)
            logger.info(f"Loaded {len(ssds)} SSD references")
    
    def _extract_location(self, html: str) -> Optional[str]:
        """Extract seller location from HTML."""
        # Try ads_contacts class first (newer format)
        contacts_match = re.search(r'class="ads_contacts"[^>]*>([^<]+)</td>', html)
        if contacts_match:
            return contacts_match.group(1).strip()
        
        # Try td_address class (older format)
        loc_match = re.search(r'class="td_address"[^>]*>([^<]+)</td>', html)
        if loc_match:
            return loc_match.group(1).strip()
        
        return None
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single SSD listing."""
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
            
            # Match to SSD reference - use title + description for better matching
            search_text = listing.title
            if listing.description:
                search_text = f"{listing.title} {listing.description}"
            
            match_result = self.matcher.match_listing(
                search_text,
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
        """Scrape all SSD listings from the category."""
        self.initialize()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page = 1
        total_listings = 0
        
        logger.info(f"Starting SSD scraper from {current_url}")
        
        while True:
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
                if limit > 0 and total_listings >= limit:
                    logger.info(f"Reached global limit ({limit})")
                    return listings
                
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
            with get_session() as session:
                existing = ListingRepository.get_by_id(session, listing.listing_id)
                
                if existing:
                    if existing.content_hash == listing.content_hash:
                        # Just update last_seen
                        session.execute(
                            "UPDATE listings SET last_seen_at = NOW() WHERE listing_id = :id",
                            {"id": listing.listing_id}
                        )
                        self.stats['unchanged'] += 1
                    else:
                        # Update with new data
                        session.execute(
                            """
                            UPDATE listings
                            SET title = :title,
                                description = :desc,
                                price_eur = :price,
                                seller_location = :location,
                                matched_ssd_id = :ssd_id,
                                ssd_confidence_score = :confidence,
                                ssd_match_method = :method,
                                capacity_gb = :capacity,
                                is_active = true,
                                last_seen_at = NOW(),
                                updated_at = NOW()
                            WHERE listing_id = :id
                            """,
                            {
                                "id": listing.listing_id,
                                "title": listing.title,
                                "desc": listing.description,
                                "price": listing.price_eur,
                                "location": listing.seller_location,
                                "ssd_id": listing.matched_ssd_id,
                                "confidence": listing.ssd_confidence_score,
                                "method": listing.ssd_match_method,
                                "capacity": listing.capacity_gb
                            }
                        )
                        self.stats['updated'] += 1
                else:
                    # Insert new
                    session.execute(
                        """
                        INSERT INTO listings (
                            listing_id, title, description, price_eur, seller_location,
                            listing_url, image_url, date_posted, category,
                            matched_ssd_id, ssd_confidence_score, ssd_match_method,
                            capacity_gb, content_hash, is_active
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image, :date, 'ssd',
                            :ssd_id, :confidence, :method,
                            :capacity, :hash, true
                        )
                        """,
                        {
                            "id": listing.listing_id,
                            "title": listing.title,
                            "desc": listing.description,
                            "price": listing.price_eur,
                            "location": listing.seller_location,
                            "url": listing.listing_url,
                            "image": listing.image_url,
                            "date": listing.date_posted,
                            "ssd_id": listing.matched_ssd_id,
                            "confidence": listing.ssd_confidence_score,
                            "method": listing.ssd_match_method,
                            "capacity": listing.capacity_gb,
                            "hash": listing.content_hash
                        }
                    )
                    self.stats['new'] += 1
                    
        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")
    
    def scrape_single(self, url: str) -> Optional[Listing]:
        """Scrape a single SSD listing by URL."""
        self.initialize()
        
        match = re.search(r'/([a-z]+)\.html$', url)
        if not match:
            logger.error(f"Could not extract listing ID from URL: {url}")
            return None
        
        listing_id = match.group(1)
        return self.scrape_listing(listing_id, url)
    
    def run(self) -> Dict[str, Any]:
        """Run full SSD scrape."""
        self.scrape_category(
            max_pages=self.config.scraper.max_pages,
            limit=self.config.scraper.max_listings
        )
        return self.stats
