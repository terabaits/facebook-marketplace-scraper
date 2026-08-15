"""Motherboard Scraper for ss.com"""
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
from src.utils.image_downloader import ImageDownloader
from src.utils.text import compute_content_hash

logger = get_logger("motherboard_scraper")


class MotherboardReference:
    """Motherboard reference data class."""
    def __init__(self, id: int, brand: str, model: str, socket: str, chipset: str, 
                 ram_slots: str, form_factor: str):
        self.id = id
        self.brand = brand
        self.model = model
        self.socket = socket
        self.chipset = chipset
        self.ram_slots = ram_slots
        self.form_factor = form_factor


class MotherboardMatcher:
    """Matcher for motherboard listings."""
    
    def __init__(self, motherboards: List[MotherboardReference]):
        self.motherboards = motherboards
        self._build_index()
        logger.info(f"MotherboardMatcher initialized with {len(motherboards)} motherboards")
    
    def _build_index(self):
        """Build search index with longer model names first for better specificity."""
        # Sort by model name length (descending) so specific variants match first
        self.motherboards.sort(key=lambda mb: len(mb.model), reverse=True)
        
        self.brand_models = {}
        for mb in self.motherboards:
            key = f"{mb.brand} {mb.model}".lower()
            self.brand_models[key] = mb
    
    def match_listing(self, title: str, description: str = "") -> tuple:
        """
        Match listing to motherboard reference.
        Returns: (matched_mb, confidence_score, match_method)
        """
        full_text = f"{title} {description}".lower()
        full_text_clean = full_text.replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
        
        best_match = None
        best_score = 0.0
        best_method = "none"
        
        for mb in self.motherboards:
            score = 0.0
            brand_matched = False
            model_matched = False
            model_score = 0.0
            
            # Brand check (required for good match)
            brand_lower = mb.brand.lower()
            brand_clean = brand_lower.replace(' ', '').replace('-', '')
            if brand_clean in full_text_clean:
                score += 0.25
                brand_matched = True
            
            # Model check - try full model first
            model_lower = mb.model.lower()
            model_clean = model_lower.replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
            
            # Check for exact model match (highest priority)
            if model_clean in full_text_clean:
                # Longer model names = more specific = higher confidence
                # Base score + length bonus
                base_score = 0.30
                length_bonus = min(0.30, len(model_clean) * 0.02)
                model_score = base_score + length_bonus
                score += model_score
                model_matched = True
            elif len(model_clean) > 6:
                # For longer models, also check if the listing contains the START of the model
                # This handles cases like listing has "h81m-vg4" but reference has "h81m-vg4-r3.0"
                partial_len = max(6, int(len(model_clean) * 0.7))  # Check first 70%
                model_start = model_clean[:partial_len]
                if model_start in full_text_clean:
                    # Partial match on longer model - should still beat shorter exact matches
                    # Score based on how much of the long model is matched
                    model_score = 0.28 + (partial_len * 0.015)  # 0.28 + up to ~0.15
                    score += model_score
                    model_matched = True
            else:
                # Check for partial model match - individual words
                model_words = model_lower.split()
                word_matches = 0
                significant_word_matches = 0
                
                for word in model_words:
                    word_clean = word.replace('-', '').replace('_', '').replace('.', '')
                    if len(word_clean) >= 3:  # Only significant words
                        if word_clean in full_text_clean:
                            word_matches += 1
                            # Give more weight to unique words
                            if len(word_clean) >= 5:
                                significant_word_matches += 1
                
                # Need at least 2 significant word matches for partial model match
                if word_matches >= 2 and significant_word_matches >= 1:
                    word_score = min(0.35, word_matches * 0.12 + significant_word_matches * 0.08)
                    score += word_score
                    model_matched = True
                elif word_matches >= 1 and significant_word_matches >= 1:
                    # Weak partial match
                    score += 0.15
            
            # Check socket mention (only if brand or model matched)
            if mb.socket and (brand_matched or model_matched):
                socket_clean = mb.socket.lower().replace(' ', '').replace('-', '')
                if socket_clean in full_text_clean:
                    score += 0.08
            
            # Check chipset mention (only if brand or model matched)
            if mb.chipset and (brand_matched or model_matched):
                chipset_clean = mb.chipset.lower().replace(' ', '').replace('-', '')
                if chipset_clean in full_text_clean:
                    score += 0.10
            
            # Penalize if brand doesn't match at all
            if not brand_matched:
                score *= 0.3  # Heavy penalty for wrong brand
            
            # Require minimum model match for decent confidence
            if not model_matched and score > 0.3:
                score = 0.2  # Cap low if no model match
            
            if score > best_score:
                best_score = score
                best_match = mb
                if score >= 0.8:
                    best_method = "exact"
                elif score >= 0.65:
                    best_method = "strong"
                elif score >= 0.45:
                    best_method = "fuzzy"
                else:
                    best_method = "weak"
        
        # Return None if confidence too low (unmatched listing)
        if best_score < 0.35:
            return None, 0.0, "none"
        
        return best_match, min(1.0, best_score), best_method
    
    def get_mb_by_id(self, mb_id: int) -> Optional[MotherboardReference]:
        """Get motherboard by ID."""
        for mb in self.motherboards:
            if mb.id == mb_id:
                return mb
        return None


class MotherboardScraper(BaseScraper):
    """Scraper for Motherboard listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/computers/completing-pc/motherboards/"
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.parser = MotherboardParser()
        self.matcher: Optional[MotherboardMatcher] = None
        
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0
        }
        self.image_downloader: Optional[ImageDownloader] = None
    
    def initialize(self):
        """Initialize database and load motherboard references."""
        logger.info("Initializing Motherboard scraper...")
        
        # Initialize database
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load motherboard reference data from database
        with get_session() as session:
            result = session.execute(text("""
                SELECT id, brand, model, socket, chipset, ram_slots, form_factor
                FROM motherboard_models
                ORDER BY brand, model
            """)).fetchall()
            
            motherboards = []
            for row in result:
                motherboards.append(MotherboardReference(
                    id=row[0],
                    brand=row[1],
                    model=row[2],
                    socket=row[3],
                    chipset=row[4],
                    ram_slots=row[5],
                    form_factor=row[6]
                ))
            
            self.matcher = MotherboardMatcher(motherboards)
            logger.info(f"Loaded {len(motherboards)} motherboard references")
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/motherboards")
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single motherboard listing."""
        try:
            result = self.crawler.fetch(url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.warning(f"Failed to fetch {url}: {result.error_msg}")
                self.stats['failed'] += 1
                return None
            
            # Skip store / business listings before parsing
            if self.parser.is_store_listing(result.html):
                logger.info(f"Skipping store/business listing {listing_id}")
                self.stats['failed'] += 1
                return None
            
            listing = self.parser.parse_listing_page(result.html, listing_id, url)
            
            if not listing:
                logger.warning(f"Failed to parse listing {listing_id}")
                self.stats['failed'] += 1
                return None
            
            # Mark listings that are bundles/combos (not just motherboard) as special
            full_text = f"{listing.title} {listing.description or ''}".lower()
            is_special = "komplektā" in full_text
            if is_special:
                logger.info(f"Marking listing {listing_id} as special: contains 'komplektā' (bundle/combo)")
            listing.is_special_listing = is_special
            listing.special_listing_reason = "Komplektā (bundle/combo)" if is_special else None
            
            # Match to motherboard reference
            search_text = listing.title
            if listing.description:
                search_text = f"{listing.title} {listing.description}"
            
            mb, confidence, method = self.matcher.match_listing(search_text)
            
            if mb:
                listing.motherboard_model_id = mb.id
                listing.motherboard_confidence_score = confidence
                listing.motherboard_match_method = method
                self.stats['matched'] += 1
                logger.info(f"Matched {listing_id}: {mb.brand} {mb.model} ({confidence:.0%} confidence)")
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
        """Scrape all motherboard listings from the category."""
        self.initialize()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page = 1
        seen_urls: Set[str] = set()
        
        logger.info(f"Starting Motherboard scraper from {current_url}")
        
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
        
        logger.info(f"Motherboard scraping complete. Stats: {self.stats}")
        return listings
    
    def _save_listing(self, listing: Listing):
        """Save listing to database."""
        try:
            with get_session() as session:
                existing = session.execute(
                    text("SELECT * FROM listings WHERE listing_id = :id AND category = 'motherboard'"),
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
                        is_special = getattr(listing, 'is_special_listing', False)
                        special_reason = getattr(listing, 'special_listing_reason', None)
                        session.execute(text("""
                            UPDATE listings
                            SET title = :title, description = :desc, price_eur = :price,
                                seller_location = :location, motherboard_model_id = :mb_id,
                                motherboard_confidence_score = :confidence,
                                motherboard_match_method = :method,
                                is_special_listing = :is_special,
                                special_listing_reason = :special_reason,
                                is_active = true, last_seen_at = NOW(), updated_at = NOW()
                            WHERE listing_id = :id
                        """), {
                            "id": listing.listing_id,
                            "title": listing.title,
                            "desc": listing.description,
                            "price": listing.price_eur,
                            "location": listing.seller_location,
                            "mb_id": getattr(listing, 'motherboard_model_id', None),
                            "confidence": getattr(listing, 'motherboard_confidence_score', None),
                            "method": getattr(listing, 'motherboard_match_method', None),
                            "is_special": is_special,
                            "special_reason": special_reason
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
                                logger.info(f"Image updated: {local_image_path}")
                                ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)
                else:
                    # Insert new
                    session.execute(text("""
                        INSERT INTO listings (
                            listing_id, title, description, price_eur, seller_location,
                            listing_url, image_url, date_posted, category,
                            motherboard_model_id, motherboard_confidence_score, motherboard_match_method,
                            content_hash, is_active
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image, NOW(), 'motherboard',
                            :mb_id, :confidence, :method,
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
                        "mb_id": getattr(listing, 'motherboard_model_id', None),
                        "confidence": getattr(listing, 'motherboard_confidence_score', None),
                        "method": getattr(listing, 'motherboard_match_method', None),
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
                            logger.info(f"Image saved locally: {local_image_path}")
                            ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")
    
    def run(self) -> Dict[str, Any]:
        """Run full motherboard scrape."""
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


class MotherboardParser:
    """Parser for motherboard listing pages."""
    
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
        
        # Look for next page link
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
        
        # Extract image - prefer full-size gallery image, fall back to thumbnail link / img
        image_url = None
        full_img = soup.find('img', {'id': 'msg_img_img'})
        if full_img:
            image_url = full_img.get('src')
        if not image_url:
            thumb_link = soup.select_one('#tr_foto a[href*=".800.jpg"]')
            if thumb_link:
                image_url = thumb_link.get('href')
        if not image_url:
            thumb_link = soup.select_one('a[href*=".800.jpg"]')
            if thumb_link:
                image_url = thumb_link.get('href')
        if not image_url:
            img = soup.find('img', {'class': 'ads_photo'})
            if img:
                image_url = img.get('src')
        
        if image_url and image_url.startswith('/'):
            image_url = f"https://i.ss.com{image_url}"
        
        listing = Listing(
            listing_id=listing_id,
            title=title,
            description=description,
            price_eur=price,
            seller_location=location,
            listing_url=url,
            image_url=image_url,
            category='motherboard'
        )
        
        return listing
    
    def is_store_listing(self, html: str) -> bool:
        """Detect store/business listings by working-hours or company rows."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for label in soup.find_all('td', {'class': 'ads_contacts_name'}):
            text = label.get_text(separator=' ', strip=True).lower()
            if ('darba' in text and 'laiks' in text) or 'uzņēmums' in text or 'uznemums' in text:
                return True
        return False
