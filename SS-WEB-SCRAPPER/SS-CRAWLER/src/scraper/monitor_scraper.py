"""Monitor Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, ScrapeRunRepository
from src.models.schemas import Listing
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.base_scraper import BaseScraper
from src.utils.config import AppConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash
from src.utils.image_downloader import ImageDownloader

logger = get_logger("monitor_scraper")


class MonitorReference:
    """Monitor reference data class."""
    def __init__(self, id: int, brand: str, model: str, size: str, 
                 resolution: str, refresh_rate: str, panel_type: str):
        self.id = id
        self.brand = brand
        self.model = model
        self.size = size
        self.resolution = resolution
        self.refresh_rate = refresh_rate
        self.panel_type = panel_type


class MonitorMatcher:
    """Matcher for monitor listings."""
    
    def __init__(self, monitors: List[MonitorReference]):
        self.monitors = monitors
        self._build_index()
        logger.info(f"MonitorMatcher initialized with {len(monitors)} monitors")
    
    def _build_index(self):
        """Build search index with longer model names first for better specificity."""
        # Sort by model name length (descending) so specific variants match first
        self.monitors.sort(key=lambda mon: len(mon.model), reverse=True)
        
        self.brand_models = {}
        for mon in self.monitors:
            key = f"{mon.brand} {mon.model}".lower()
            self.brand_models[key] = mon
    
    def _extract_size_from_text(self, text: str) -> Optional[str]:
        """Extract monitor size from text (e.g., '24', '27', '32')."""
        # Match patterns like "24", "24\"", "24 inch", "27.5"
        size_patterns = [
            r'\b(\d+(?:\.\d+)?)\s*["\']?\s*(?:inch|\"|\')',
            r'\b(\d{2,3})\s*["\']',
            r'\b(\d{2,3})\s*(?:inch|in)\b',
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text.lower())
            if match:
                size = match.group(1)
                # Clean up common sizes
                if '.' in size:
                    return size
                return size
        
        return None
    
    def _extract_resolution_from_text(self, text: str) -> Optional[str]:
        """Extract resolution from text."""
        res_patterns = [
            r'\b(1920\s*x\s*1080|1080p|fhd|full\s*hd)\b',
            r'\b(2560\s*x\s*1440|1440p|qhd|wqhd)\b',
            r'\b(3840\s*x\s*2160|2160p|4k|uhd)\b',
            r'\b(3440\s*x\s*1440|ultrawide)\b',
            r'\b(5120\s*x\s*1440)\b',
        ]
        
        for pattern in res_patterns:
            match = re.search(pattern, text.lower())
            if match:
                res = match.group(1)
                # Normalize
                if '1080' in res or 'fhd' in res:
                    return "1920x1080"
                elif '1440' in res or 'qhd' in res or 'wqhd' in res:
                    return "2560x1440"
                elif '2160' in res or '4k' in res or 'uhd' in res:
                    return "3840x2160"
                elif '3440' in res:
                    return "3440x1440"
                return res
        
        return None
    
    def _extract_refresh_rate(self, text: str) -> Optional[str]:
        """Extract refresh rate from text."""
        refresh_patterns = [
            r'\b(\d{2,3})\s*hz\b',
            r'\b(\d{2,3})\s*hertz\b',
            r'\b(\d{2,3})\s*гц\b',  # Cyrillic
        ]
        
        for pattern in refresh_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        
        return None
    
    def _extract_panel_type(self, text: str) -> Optional[str]:
        """Extract panel type from text."""
        panel_patterns = [
            r'\b(ips|va|tn|oled|mini[-\s]?led|qled)\b',
        ]
        
        for pattern in panel_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).upper()
        
        return None
    
    def match_listing(self, title: str, description: str = "") -> tuple:
        """
        Match listing to monitor reference.
        Returns: (matched_monitor, confidence_score, match_method)
        """
        full_text = f"{title} {description}".lower()
        
        # Extract specs from listing
        extracted_size = self._extract_size_from_text(full_text)
        extracted_resolution = self._extract_resolution_from_text(full_text)
        extracted_refresh = self._extract_refresh_rate(full_text)
        extracted_panel = self._extract_panel_type(full_text)
        
        best_match = None
        best_score = 0.0
        best_method = "none"
        best_brand_matched = False
        
        for mon in self.monitors:
            score = 0.0
            matches = 0
            
            # Check brand match
            brand_clean = mon.brand.lower().replace(' ', '')
            brand_matched = brand_clean in full_text.replace(' ', '')
            if brand_matched:
                score += 0.25
                matches += 1
                if '203v5' in mon.model.lower():
                    logger.info(f"  +Brand match: +25%")
            
            # Check model match - try full model first
            model_clean = mon.model.lower().replace(' ', '').replace('-', '').replace('_', '')
            full_text_clean = full_text.replace(' ', '').replace('-', '').replace('_', '')
            
            if model_clean in full_text_clean:
                # Full model match - highest confidence
                score += 0.45  # Boosted for exact match
                matches += 2
            else:
                # Only check parts if the full model didn't match
                # Check if just the model number (last part) is in text
                model_parts = mon.model.split()
                if len(model_parts) >= 1:
                    for part in model_parts:
                        part_clean = part.lower().replace('-', '').replace('_', '')
                        if len(part_clean) >= 5:  # Only longer significant parts
                            if part_clean in full_text_clean:
                                score += 0.20
                                matches += 1
                                break
                
                # Also check for model number/ID at the end
                # e.g., "Pavilion w2007v" - check if "w2007v" is in text
                model_words = mon.model.lower().split()
                if len(model_words) >= 2:
                    # Last word is likely the model number
                    last_word = model_words[-1].replace('-', '').replace('_', '')
                    if len(last_word) >= 3:
                        # Check if model number exists in text
                        idx = full_text_clean.find(last_word)
                        if idx != -1:
                            # Check that it's not a substring of a longer model number
                            # e.g., "w20" should not match "w2007v"
                            end_pos = idx + len(last_word)
                            if end_pos >= len(full_text_clean) or not full_text_clean[end_pos].isdigit():
                                # Exact model number match - high confidence!
                                score += 0.40  # Boosted from 0.25 to 0.40
                                matches += 2
                
                # Also check for partial model match (e.g., "34WP65" from "34WP65G-B")
                # This handles cases where model numbers are similar but not exact
                if len(model_clean) >= 6:
                    # Extract model number without suffix (e.g., "34wp65" from "34wp65gb")
                    model_base = model_clean[:6]  # First 6 chars (e.g., "34wp65")
                    if '203v5' in mon.model.lower():
                        logger.info(f"  Checking partial: {model_base} in text={model_base in full_text_clean}")
                    if model_base in full_text_clean:
                        score += 0.25
                        matches += 1
                        if '203v5' in mon.model.lower():
                            logger.info(f"  +Partial match: +25%")
            
            # Check size match
            if mon.size and extracted_size:
                size_matched = mon.size.replace('"', '').replace("'", '').strip() == extracted_size
                if '203v5' in mon.model.lower():
                    logger.info(f"  Size check: {mon.size} vs {extracted_size}: {size_matched}")
                if size_matched:
                    score += 0.15
                    matches += 1
                    if '203v5' in mon.model.lower():
                        logger.info(f"  +Size match: +15%")
            
            # Check resolution match
            if mon.resolution and extracted_resolution:
                if mon.resolution.lower() == extracted_resolution.lower():
                    score += 0.1
                    matches += 1
            
            # Check refresh rate match
            if mon.refresh_rate and extracted_refresh:
                if mon.refresh_rate == extracted_refresh:
                    score += 0.1
                    matches += 1
            
            # Check panel type match
            if mon.panel_type and extracted_panel:
                if mon.panel_type.lower() == extracted_panel.lower():
                    score += 0.05
                    matches += 1
            
            if score > best_score and brand_matched:
                best_score = score
                best_match = mon
                best_brand_matched = brand_matched
                if '203v5' in mon.model.lower():
                    logger.info(f"DEBUG 203V5: {mon.model} score={score:.0%}, matches={matches}")
                if matches >= 5:
                    best_method = "exact"
                elif matches >= 3:
                    best_method = "high"
                elif matches >= 2:
                    best_method = "fuzzy"
                else:
                    best_method = "partial"
        
        # Only return a match if brand matched and score is decent
        if best_match and best_brand_matched and best_score >= 0.45:
            logger.info(f"MATCH: {best_match.brand} {best_match.model} at {best_score:.0%}")
            return best_match, min(1.0, best_score), best_method
        if best_match:
            logger.info(f"Low confidence: {best_match.brand} {best_match.model} ({best_score:.0%}) - below threshold")
        else:
            logger.info(f"No match found for text: {search_text[:50]}")
        
        return None, 0.0, "none"
    
    def get_monitor_by_id(self, monitor_id: int) -> Optional[MonitorReference]:
        """Get monitor by ID."""
        for mon in self.monitors:
            if mon.id == monitor_id:
                return mon
        return None


class MonitorScraper(BaseScraper):
    """Scraper for Monitor listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/computers/monitors/"
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.parser = MonitorParser()
        self.matcher: Optional[MonitorMatcher] = None
        
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'images_downloaded': 0,
        }
        self.image_downloader: Optional[ImageDownloader] = None
    
    def initialize(self):
        """Initialize database and load monitor references."""
        logger.info("Initializing Monitor scraper...")
        
        # Initialize database
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load monitor reference data from database
        with get_session() as session:
            result = session.execute(text("""
                SELECT id, brand, model, size, resolution, refresh_rate, panel_type
                FROM monitor_models
                ORDER BY brand, model
            """)).fetchall()
            
            monitors = []
            for row in result:
                monitors.append(MonitorReference(
                    id=row[0],
                    brand=row[1],
                    model=row[2],
                    size=row[3],
                    resolution=row[4],
                    refresh_rate=row[5],
                    panel_type=row[6]
                ))
            
            self.matcher = MonitorMatcher(monitors)
            logger.info(f"Loaded {len(monitors)} monitor references")
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/monitor")
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single monitor listing."""
        try:
            result = self.crawler.fetch(url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.warning(f"Failed to fetch {url}: {result.error_msg}")
                self.stats['failed'] += 1
                return None
            
            listing = self.parser.parse_listing_page(result.html, listing_id, url)
            
            if not listing:
                logger.warning(f"Failed to parse listing {listing_id}")
                self.stats['failed'] += 1
                return None
            
            # Match to monitor reference
            search_text = listing.title
            if listing.description:
                search_text = f"{listing.title} {listing.description}"
            
            logger.info(f"Search text: '{search_text}'")
            
            mon, confidence, method = self.matcher.match_listing(search_text)
            
            if mon and confidence >= self.config.scraper.min_confidence_threshold:
                listing.monitor_model_id = mon.id
                listing.monitor_confidence_score = confidence
                listing.monitor_match_method = method
                self.stats['matched'] += 1
                logger.info(f"Matched {listing_id}: {mon.brand} {mon.model} ({confidence:.0%} confidence)")
            else:
                if mon:
                    logger.info(f"Low confidence for {listing_id}: {mon.brand} {mon.model} ({confidence:.0%}) - below threshold")
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
        """Scrape all monitor listings from the category."""
        self.initialize()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page = 1
        seen_urls: Set[str] = set()
        
        logger.info(f"Starting Monitor scraper from {current_url}")
        
        while True:
            if max_pages > 0 and page > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break
            
            logger.info(f"Fetching page {page}: {current_url}")
            
            result = self.crawler.fetch(current_url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.error(f"Failed to fetch page {page}: {result.error_msg}")
                break
            
            listing_urls = self.parser.extract_listing_urls(result.html, self.BASE_URL)
            new_listings = [(lid, url) for lid, url in listing_urls if url not in seen_urls]
            seen_urls.update(url for _, url in new_listings)
            
            logger.info(f"Found {len(listing_urls)} listings on page {page}, {len(new_listings)} new")
            
            for listing_id, url in new_listings:
                if limit > 0 and len(listings) >= limit:
                    logger.info(f"Reached global limit ({limit})")
                    return listings
                
                listing = self.scrape_listing(listing_id, url)
                
                if listing:
                    self._save_listing(listing)
                    listings.append(listing)
                
                self.stats['processed'] += 1
            
            pagination = self.parser.extract_pagination_info(result.html)
            has_next = pagination.get('has_next', False)
            next_url = pagination.get('next_url')
            
            if not has_next or not next_url:
                logger.info("No more pages")
                break
            
            current_url = next_url if next_url.startswith('http') else f"{self.BASE_URL}{next_url}"
            page += 1
        
        logger.info(f"Monitor scraping complete. Stats: {self.stats}")
        return listings
    
    def _save_listing(self, listing: Listing):
        """Save listing to database."""
        try:
            with get_session() as session:
                existing = session.execute(
                    text("SELECT * FROM listings WHERE listing_id = :id AND category = 'monitor'"),
                    {"id": listing.listing_id}
                ).fetchone()
                
                if existing:
                    if existing.content_hash == listing.content_hash:
                        session.execute(
                            text("UPDATE listings SET last_seen_at = NOW() WHERE listing_id = :id"),
                            {"id": listing.listing_id}
                        )
                        self.stats['unchanged'] += 1
                        logger.info(f"⏸️ {listing.listing_id}: Unchanged")
                    else:
                        # Save version history
                        session.execute(text("""
                            INSERT INTO price_history (listing_id, price_eur, recorded_at, change_type)
                            SELECT listing_id, price_eur, NOW(), 'price'
                            FROM listings WHERE listing_id = :id
                        """), {"id": listing.listing_id})
                        
                        # Update
                        session.execute(text("""
                            UPDATE listings
                            SET title = :title, description = :desc, price_eur = :price,
                                seller_location = :location, monitor_model_id = :mon_id,
                                monitor_confidence_score = :confidence,
                                monitor_match_method = :method,
                                is_active = true, last_seen_at = NOW(), updated_at = NOW()
                            WHERE listing_id = :id
                        """), {
                            "id": listing.listing_id,
                            "title": listing.title,
                            "desc": listing.description,
                            "price": listing.price_eur,
                            "location": listing.seller_location,
                            "mon_id": getattr(listing, 'monitor_model_id', None),
                            "confidence": getattr(listing, 'monitor_confidence_score', None),
                            "method": getattr(listing, 'monitor_match_method', None)
                        })
                        self.stats['updated'] += 1
                        logger.info(f"💰 {listing.listing_id}: Updated")
                        
                        # Download/update image if available
                        if listing.image_url and self.image_downloader:
                            local_image_path = self.image_downloader.download_image(
                                listing.image_url,
                                listing.listing_id
                            )
                            if local_image_path:
                                self.stats['images_downloaded'] += 1
                                logger.info(f"Image updated: {local_image_path}")
                                ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)
                else:
                    # Insert new
                    session.execute(text("""
                        INSERT INTO listings (
                            listing_id, title, description, price_eur, seller_location,
                            listing_url, image_url, date_posted, category,
                            monitor_model_id, monitor_confidence_score, monitor_match_method,
                            content_hash, is_active
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image, NOW(), 'monitor',
                            :mon_id, :confidence, :method,
                            :hash, true
                        )
                    """), {
                        "id": listing.listing_id,
                        "title": listing.title,
                        "desc": listing.description,
                        "price": listing.price_eur,
                        "location": listing.seller_location,
                        "url": listing.listing_url,
                        "image": listing.image_url,
                        "mon_id": getattr(listing, 'monitor_model_id', None),
                        "confidence": getattr(listing, 'monitor_confidence_score', None),
                        "method": getattr(listing, 'monitor_match_method', None),
                        "hash": listing.content_hash
                    })
                    self.stats['new'] += 1
                    logger.info(f"✨ {listing.listing_id}: New")
                    
                    # Download image if available
                    if listing.image_url and self.image_downloader:
                        local_image_path = self.image_downloader.download_image(
                            listing.image_url,
                            listing.listing_id
                        )
                        if local_image_path:
                            self.stats['images_downloaded'] += 1
                            logger.info(f"Image saved locally: {local_image_path}")
                            ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")
    
    def run(self) -> Dict[str, Any]:
        """Run full monitor scrape."""
        self.scrape_category(
            max_pages=self.config.scraper.max_pages,
            limit=self.config.scraper.max_listings
        )
        return self.stats
    
    def get_stats(self) -> Dict[str, int]:
        """Get current scrape statistics."""
        return self.stats.copy()
    
    def scrape_single(self, url: str) -> Optional[Listing]:
        """Scrape a single URL for testing."""
        self.initialize()
        
        # Extract listing ID from URL
        match = re.search(r'/([a-z0-9]+)\.html$', url)
        if not match:
            logger.error(f"Could not extract listing ID from URL: {url}")
            return None
        
        listing_id = match.group(1)
        return self.scrape_listing(listing_id, url)


class MonitorParser:
    """Parser for monitor listing pages."""
    
    def extract_listing_urls(self, html: str, base_url: str) -> List[tuple]:
        """Extract listing URLs from category page HTML."""
        from bs4 import BeautifulSoup
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=re.compile(r'/msg/lv/electronics/.*\.html$')):
            href = link.get('href', '')
            if href:
                match = re.search(r'/([a-z0-9]+)\.html$', href)
                if match:
                    listing_id = match.group(1)
                    full_url = href if href.startswith('http') else f"{base_url}{href}"
                    urls.append((listing_id, full_url))
        
        return urls
    
    def extract_pagination_info(self, html: str) -> Dict[str, Any]:
        """Extract pagination info from category page."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        has_next = False
        next_url = None
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            if 'Nākamie' in text or 'next' in text.lower():
                has_next = True
                next_url = link.get('href')
                break
        
        return {
            'has_next': has_next,
            'next_url': next_url
        }
    
    def parse_listing_page(self, html: str, listing_id: str, url: str) -> Optional[Listing]:
        """Parse a single listing page."""
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_elem = soup.find('title')
        title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""
        
        # Extract description
        msg_div = soup.find('div', {'id': 'msg_div_msg'})
        description = ""
        if msg_div:
            description = msg_div.get_text(separator=' ', strip=True)
        
        # Extract price
        price = 0.0
        price_cell = soup.find('td', {'class': 'ads_price'})
        if price_cell:
            price_text = price_cell.get_text(strip=True)
            price_match = re.search(r'([\d\s,]+)', price_text.replace(' ', ''))
            if price_match:
                price_str = price_match.group(1).replace(',', '.').replace(' ', '')
                try:
                    price = float(price_str)
                except ValueError:
                    pass
        
        # Extract location
        location = ""
        for row in soup.find_all('tr'):
            label = row.find('td', {'class': 'ads_contacts_name'})
            if label and 'vieta' in label.get_text(strip=True).lower():
                value_cell = row.find('td', {'class': 'ads_contacts'})
                if value_cell:
                    location = value_cell.get_text(strip=True)
                    break
        
        # Extract image - prefer full-size gallery image, then thumbnail link, then any preview image.
        image_url = None
        main_img = soup.find('img', {'id': 'msg_img_img'})
        if main_img and main_img.get('src'):
            image_url = main_img['src']
        if not image_url:
            thumb_link = soup.select_one('#tr_foto a[href*=".800.jpg"]')
            if thumb_link and thumb_link.get('href'):
                image_url = thumb_link['href']
        if not image_url:
            img = soup.find('img', {'class': 'ads_photo'})
            if img:
                image_url = img.get('src')

        if image_url and image_url.startswith('/'):
            image_url = f"https://i.ss.com{image_url}"
        
        # Extract brand/model from options table (e.g., Marka: Hp W2007v)
        brand_model = ""
        # Try multiple selectors for brand/model
        for row in soup.find_all('tr'):
            opt_name = row.find('td', {'class': 'ads_opt_name'})
            if opt_name:
                label_text = opt_name.get_text(strip=True).lower()
                if 'marka' in label_text or 'brand' in label_text:
                    # Find the corresponding value cell - could be ads_opt or have id like tdo_*
                    opt_value = row.find('td', {'class': 'ads_opt'})
                    if opt_value:
                        # Get text including from nested elements like <b>
                        value_text = ' '.join(opt_value.stripped_strings)
                        if value_text:
                            brand_model = value_text
                            logger.debug(f"Found brand/model: {brand_model}")
                            break
        
        # Also try looking for the specific tdo_51 pattern
        if not brand_model:
            tdo_cell = soup.find('td', {'id': 'tdo_51'})
            if tdo_cell:
                brand_model = ' '.join(tdo_cell.stripped_strings)
                logger.debug(f"Found brand/model via tdo_51: {brand_model}")
        
        # Append brand/model to description if found
            description = f"{brand_model} {description}".strip()
        
        listing = Listing(
            listing_id=listing_id,
            title=title,
            description=description,
            price_eur=price,
            seller_location=location,
            listing_url=url,
            image_url=image_url,
            category='monitor'
        )
        
        return listing
