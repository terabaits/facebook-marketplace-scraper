"""CPU scraper for ss.com."""
from datetime import datetime
from typing import Iterator, Tuple, Optional
from pathlib import Path

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, CPUReferenceRepository, ScrapeRunRepository
from src.models.schemas import Listing, CPUMatchResult
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.cpu_parser import CPUListingParser
from src.scraper.cpu_matcher import CPUMatcher
from src.utils.config import AppConfig, ScraperConfig
from src.utils.logger import get_logger

logger = get_logger("cpu_scraper")


class CPUScraper:
    """CPU scraper orchestrator."""
    
    CPU_CATEGORY_PATH = "/lv/electronics/computers/completing-pc/cpu/"
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.matcher: Optional[CPUMatcher] = None
        
        # Stats tracking
        self.stats = {
            'total': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'unmatched': 0,
            'low_confidence': 0,
        }
    
    def initialize(self):
        """Initialize database and load CPU references."""
        logger.info("Initializing CPU scraper...")
        
        # Initialize database
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load CPU reference data
        with get_session() as session:
            cpus = CPUReferenceRepository.get_all(session)
            self.matcher = CPUMatcher(cpus)
        
        logger.info(f"Loaded {len(cpus)} CPU references")
        
        # Ensure HTML samples directory
        if self.config.scraper.save_html_samples:
            Path(self.config.scraper.html_samples_dir).mkdir(parents=True, exist_ok=True)
    
    def _process_listing(self, html: str, url: str) -> Tuple[Optional[Listing], str, str]:
        """
        Parse and process a single CPU listing.
        
        Returns:
            Tuple of (listing, action, message)
            action: 'new', 'updated', 'unchanged', 'failed', 'unmatched', 'low_confidence'
        """
        # Parse HTML
        parser = CPUListingParser(html, url)
        listing = parser.parse()
        
        if not listing:
            # Save HTML sample for debugging
            if self.config.scraper.save_html_samples:
                self.crawler.save_html_sample(html, f"cpu_parse_failed_{datetime.now().strftime('%H%M%S')}")
            return None, 'failed', 'Parse error: Could not extract listing data'
        
        # Match CPU
        action = 'new'
        message = 'Processed: new'
        
        if self.matcher:
            match_result = self.matcher.match(
                listing.title, 
                listing.description or "",
                base_freq_mhz=listing.base_freq_mhz
            )
            
            if match_result.cpu:
                listing.matched_cpu_id = match_result.cpu.id
                listing.cpu_confidence_score = match_result.confidence
                listing.cpu_match_method = match_result.method
                
                # Check confidence threshold
                if match_result.confidence < self.config.scraper.min_confidence_threshold:
                    action = 'low_confidence'
                    message = f"Match confidence {match_result.confidence:.2f} below threshold"
            else:
                action = 'unmatched'
                message = 'No CPU match found'
        
        # Save to database (ALL listings, including unmatched)
        with get_session() as session:
            _, db_action = ListingRepository.create_or_update(session, listing, run_id=0)
            if action == 'new':
                action = db_action
                message = f"Processed: {db_action}"
        
        return listing, action, message
    
    def _scrape_category_page(self, page_url: str, run_id: int) -> Iterator[Tuple[str, str, str]]:
        """
        Scrape listings from a CPU category page.
        
        Yields:
            Tuple of (url, action, message) for each listing
        """
        logger.info(f"Fetching CPU category: {page_url}")
        
        result = self.crawler.fetch(page_url, "CPU category page")
        
        if result.error_type != ErrorType.SUCCESS:
            logger.error(f"Failed to fetch category: {result.error_msg}")
            return
        
        # Parse category page for links
        parser = CPUListingParser(result.html, page_url)
        links = parser.get_category_links()
        
        # Apply limit if in test mode
        if self.config.scraper.test_mode and self.config.scraper.max_listings > 0:
            links = links[:self.config.scraper.max_listings]
            logger.info(f"Test mode: limiting to {len(links)} listings")
        
        logger.info(f"Found {len(links)} CPU listings to process")
        
        for idx, link in enumerate(links, 1):
            self.stats['total'] += 1
            
            # Fetch listing
            listing_result = self.crawler.fetch(link, f"CPU listing {idx}/{len(links)}")
            
            if listing_result.error_type != ErrorType.SUCCESS:
                self.stats['failed'] += 1
                yield link, 'failed', f"Fetch failed: {listing_result.error_msg}"
                
                if listing_result.error_type == ErrorType.BLOCKED:
                    logger.critical("Scraping blocked! Stopping immediately.")
                    break
                continue
            
            # Process listing
            listing, action, message = self._process_listing(listing_result.html, link)
            
            self.stats[action] += 1
            yield link, action, message
    
    def run(self) -> dict:
        """
        Run the CPU scraping process.
        
        Returns:
            Statistics dictionary
        """
        self.initialize()
        
        # Create scrape run record
        with get_session() as session:
            run_id = ScrapeRunRepository.create(
                session,
                category='cpu',
                config={
                    'test_mode': self.config.scraper.test_mode,
                    'max_listings': self.config.scraper.max_listings,
                    'min_confidence': self.config.scraper.min_confidence_threshold
                }
            )
        
        logger.info(f"CPU scrape run started: ID {run_id}")
        
        try:
            # Build starting URL
            base = f"{self.config.scraper.base_url}{self.CPU_CATEGORY_PATH}"
            page_num = 1
            has_more = True
            
            while has_more:
                page_url = base if page_num == 1 else f"{base}page{page_num}.html"
                
                for link, action, message in self._scrape_category_page(page_url, run_id):
                    logger.info(f"{action.upper()}: {message}")
                
                # Check for next page
                page_num += 1
                
                # Stop if we've processed enough listings
                if self.config.scraper.max_listings > 0:
                    if self.stats['total'] >= self.config.scraper.max_listings:
                        logger.info(f"Listing limit reached: {self.stats['total']} listings")
                        has_more = False
                
                # Stop if we've reached max pages
                if self.config.scraper.max_pages > 0:
                    if page_num > self.config.scraper.max_pages:
                        logger.info(f"Page limit reached ({self.config.scraper.max_pages}), stopping")
                        has_more = False
            
            # Mark stale listings
            with get_session() as session:
                stale_count = ListingRepository.mark_stale(session, days=self.config.scraper.stale_after_days)
                if stale_count:
                    logger.info(f"Marked {stale_count} listings as stale")
            
            # Complete scrape run
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'completed',
                    'total': self.stats['total'],
                    'new': self.stats['new'],
                    'updated': self.stats['updated'],
                    'skipped': self.stats['unchanged'],
                    'failed': self.stats['failed']
                })
            
            logger.info("CPU scraping completed successfully")
            
        except Exception as e:
            logger.critical(f"CPU scraping failed: {e}")
            
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'failed',
                    'error': str(e),
                    **self.stats
                })
            
            raise
        
        return self.stats
    
    def run_single(self, url: str) -> Tuple[Optional[Listing], CPUMatchResult]:
        """
        Scrape a single CPU URL (for testing/debugging).
        
        Returns:
            Tuple of (listing, match_result)
        """
        self.initialize()
        
        logger.info(f"Single URL mode: {url}")
        
        result = self.crawler.fetch(url, "single CPU listing")
        
        if result.error_type != ErrorType.SUCCESS:
            logger.error(f"Fetch failed: {result.error_msg}")
            return None, CPUMatchResult(confidence=0.0, method="failed")
        
        listing, action, message = self._process_listing(result.html, url)
        
        if listing and self.matcher:
            match = self.matcher.match(
                listing.title, 
                listing.description or "",
                base_freq_mhz=listing.base_freq_mhz
            )
            return listing, match
        
        return listing, CPUMatchResult(confidence=0.0, method="none")
