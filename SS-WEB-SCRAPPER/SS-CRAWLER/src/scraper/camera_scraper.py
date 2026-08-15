"""Camera Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, ScrapeRunRepository
from src.models.schemas import Listing
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.parser import ListingParser
from src.scraper.camera_matcher import CameraMatcher
from src.utils.config import AppConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash

from src.utils.image_downloader import ImageDownloader

logger = get_logger("camera_scraper")


class CameraScraper:
    """Scraper for camera listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URLS = [
        "/lv/electronics/photo-optics/slr-cameras/",
        "/lv/electronics/photo-optics/digital-cameras/"
    ]
    
    # Filter patterns (case insensitive)
    FILTER_BRANDS = ['nikon']
    FILTER_MODELS = ['powershot', 'nex']  # Compact cameras to filter out
    FILTER_STORES = ['internetveikals', 'jauns ar 2 gadu garantiju']
    FILTER_CONDITION = ['jauns']
    
    def __init__(self, config: AppConfig, category_url: str = None):
        """Initialize the camera scraper.
        
        Args:
            config: AppConfig instance
            category_url: Optional specific category URL to scrape. If None, scrapes all.
        """
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.camera_references = []
        self.matcher = None
        self.category_url = category_url
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'filtered': 0,
            'passed_filter_unmatched': 0,
            'matched_unchanged': 0
        }
        self.image_downloader: Optional[ImageDownloader] = None
    
    def initialize(self):
        """Initialize database and load camera references."""
        logger.info("Initializing Camera scraper...")
        init_database(self.config.database)
        
        # Load camera references from database
        with get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT * FROM camera_reference"))
            self.camera_references = [dict(row._mapping) for row in result.fetchall()]
            logger.info(f"Loaded {len(self.camera_references)} camera references")
        
        # Initialize matcher
        self.matcher = CameraMatcher(self.camera_references)
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/cameras")
    
    def get_stats(self) -> Dict[str, int]:
        """Return current scrape statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset scrape statistics."""
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'filtered': 0,
            'passed_filter_unmatched': 0,
            'matched_unchanged': 0
        }
    
    def _should_filter(self, title: str, description: str = "") -> tuple[bool, str]:
        """
        Check if listing should be filtered out.
        Returns (should_filter, reason)
        """
        full_text = f"{title} {description}".lower()
        
        # Check for Nikon brand
        if 'nikon' in full_text:
            return True, "filtered_nikon"
        
        # Check for compact cameras (PowerShot, NEX)
        for model_filter in self.FILTER_MODELS:
            if model_filter in full_text:
                return True, f"filtered_{model_filter}"
        
        # Check for "Jauns ar 2 gadu garantiju" (new with 2 year warranty)
        if 'jauns ar 2 gadu garantiju' in full_text:
            return True, "filtered_new_warranty"
        
        # Check for online stores
        if 'internetveikals' in full_text:
            return True, "filtered_internetveikals"
        
        # Check for "new" condition
        if 'jauns' in full_text:
            return True, "filtered_jauns"
        
        return False, ""
    
    def _extract_location(self, html: str) -> Optional[str]:
        """Extract seller location from HTML."""
        contacts_match = re.search(r'class="ads_contacts"[^\u003e]*\u003e([^\u003c]+)\u003c/td\u003e', html)
        if contacts_match:
            return contacts_match.group(1).strip()
        
        loc_match = re.search(r'class="td_address"[^\u003e]*\u003e([^\u003c]+)\u003c/td\u003e', html)
        if loc_match:
            return loc_match.group(1).strip()
        
        return None
    
    def _match_camera(self, title: str, description: str = "") -> tuple[Optional[int], float, str]:
        """
        Match camera listing to reference database.
        Returns (matched_camera_id, confidence_score, match_method)
        """
        result = self.matcher.match(title, description)
        
        if result.camera and result.confidence >= 0.5:
            camera_id = result.camera.get('id')
            logger.info(f"Matched camera: {result.camera.get('brand')} {result.camera.get('model')} ({result.confidence:.0%} confidence)")
            return camera_id, result.confidence, result.method
        
        return None, result.confidence, result.method
    
    def _match_lenses(self, title: str, description: str = "") -> List[Dict[str, Any]]:
        """
        Check if listing mentions any lenses.
        Returns list of matched lenses from existing lens reference.
        """
        # Import lens matcher
        from src.database.repository import LensReferenceRepository
        
        matched_lenses = []
        full_text = f"{title} {description}".lower()
        
        with get_session() as session:
            lenses = LensReferenceRepository.get_all(session)
            
            for lens in lenses:
                lens_name = lens.get('lens_name', '').lower()
                brand = lens.get('brand', '').lower()
                focal_min = lens.get('focal_length_mm')
                focal_max = lens.get('max_focal_length_mm')
                
                # Skip if no lens name
                if not lens_name:
                    continue
                
                score = 0.0
                focal_match_score = 0.0
                
                # Check lens name patterns - MUST match focal length first
                # Require BOTH brand AND focal length pattern
                focal_pattern = re.search(r'(\d+)(?:\s*-\s*(\d+))?\s*mm', lens_name)
                if focal_pattern and brand and brand in full_text:
                    lens_focal = focal_pattern.group(1)
                    lens_focal_max = focal_pattern.group(2)
                    
                    if lens_focal_max:
                        # Zoom lens: check for N-N pattern with or without mm
                        zoom_patterns = [
                            rf'\b{re.escape(lens_focal)}\s*-\s*{re.escape(lens_focal_max)}\b',  # 18-55
                            rf'\b{re.escape(lens_focal)}\s*-\s*{re.escape(lens_focal_max)}\s*mm\b',  # 18-55mm
                        ]
                        for pattern in zoom_patterns:
                            if re.search(pattern, full_text, re.IGNORECASE):
                                focal_match_score = 0.8
                                break
                    else:
                        # Prime lens: check for Nmm or N mm
                        # But NOT when preceded by hyphen (part of zoom range like "18-45")
                        prime_patterns = [
                            rf'(?<!\d-)(?<!-)\b{re.escape(lens_focal)}\s*mm\b',
                            rf'(?<!\d-)(?<!-)\b{re.escape(lens_focal)}mm\b',
                        ]
                        for pattern in prime_patterns:
                            if re.search(pattern, full_text, re.IGNORECASE):
                                focal_match_score = 0.7
                                break
                
                # If focal length matched, add bonuses for brand and features
                if focal_match_score > 0:
                    score = focal_match_score
                    
                    # Bonus for brand
                    if brand and brand in full_text:
                        score += 0.1
                    
                    # Bonus if full lens name appears
                    if lens_name.replace('/', ' ').lower() in full_text:
                        score += 0.05
                    
                    # Small bonus for keywords (max 0.1)
                    lens_keywords = lens_name.replace('mm', '').replace('f/', '').replace('/', ' ').split()
                    keyword_matches = sum(1 for kw in lens_keywords if len(kw) > 2 and kw.lower() in full_text)
                    if lens_keywords:
                        score += (keyword_matches / min(len(lens_keywords), 4)) * 0.1
                
                # Check aperture in lens name
                aperture_match = re.search(r'f[/\.\s]*(\d+\.?\d*)', lens_name)
                if aperture_match:
                    aperture = aperture_match.group(1)
                    if aperture in full_text:
                        score += 0.2
                
                if score >= 0.5:
                    lens_id = f"{lens.get('brand', '')}_{lens.get('lens_name', '')}".replace(' ', '_').replace('/', '_')
                    matched_lenses.append({
                        'lens_id': lens_id,
                        'lens_name': lens.get('lens_name'),
                        'brand': lens.get('brand'),
                        'confidence': min(score, 1.0)
                    })
        
        # Return best match only, or deduplicate by focal length
        matched_lenses.sort(key=lambda x: x['confidence'], reverse=True)
        
        # If multiple lenses match same focal range, keep only the best
        seen_ranges = {}
        for lens in matched_lenses:
            lens_name = lens['lens_name']
            # Extract focal range from lens name
            focal_match = re.search(r'(\d+)-?(\d+)?mm', lens_name.lower())
            if focal_match:
                focal_range = f"{focal_match.group(1)}-{focal_match.group(2) if focal_match.group(2) else 'prime'}"
                if focal_range not in seen_ranges:
                    seen_ranges[focal_range] = lens
        
        # Return deduplicated list (best match per focal range), keep up to 3 lenses
        return list(seen_ranges.values())[:3]
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single camera listing."""
        try:
            self.stats['processed'] += 1
            
            result = self.crawler.fetch(url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.error(f"Failed to fetch listing {listing_id}: {result.error_msg}")
                self.stats['failed'] += 1
                return None
            
            parser = ListingParser(result.html, url)
            listing = parser.parse()
            
            if not listing:
                logger.warning(f"Failed to parse listing {listing_id}")
                self.stats['failed'] += 1
                return None
            
            brand = parser._extract_brand_model() or ""
            desc = parser._extract_description() or ""
            
            model = ""
            for label_td in parser.soup.find_all('td', class_='ads_opt_name'):
                label_text = label_td.get_text(strip=True).lower()
                if 'modelis' in label_text or 'model' in label_text:
                    value_td = label_td.find_next_sibling('td', class_='ads_opt')
                    if value_td:
                        model = value_td.get_text(strip=True)
                        break
            
            title_parts = []
            if brand:
                title_parts.append(brand)
            if model and model != brand:
                title_parts.append(f"Modelis: {model}")
            
            if desc:
                first_sentence = desc.split('.')[0][:200]
                title_parts.append(first_sentence)
            
            if title_parts:
                title = " ".join(title_parts).strip()
            elif brand:
                title = brand
            elif desc:
                title = desc[:200]
            else:
                title = "Unknown"
            
            listing.title = title
            listing.listing_id = listing_id
            listing.category = 'camera'
            
            location = self._extract_location(result.html)
            if location:
                listing.seller_location = location
            
            should_filter, filter_reason = self._should_filter(listing.title, listing.description or "")
            if should_filter:
                logger.info(f"Filtered [{listing_id}]: {filter_reason}")
                self.stats['filtered'] += 1
                return None
            
            # Match camera body
            matched_camera_id, confidence, method = self._match_camera(listing.title, listing.description or "")
            if matched_camera_id:
                listing.matched_camera_id = matched_camera_id
                listing.camera_confidence_score = confidence
                listing.camera_match_method = method
                self.stats['matched'] += 1
                
                # Get camera info for logging
                camera_info = self.matcher.get_camera_by_id(matched_camera_id)
                if camera_info:
                    logger.info(f"Matched [{listing_id}]: {camera_info.get('brand')} {camera_info.get('model')} ({confidence:.0%} confidence)")
            else:
                listing.matched_camera_id = None
                listing.camera_confidence_score = confidence
                listing.camera_match_method = method
                self.stats['passed_filter_unmatched'] += 1
                logger.info(f"No camera match for [{listing_id}]")
            
            # Check for lenses in listing
            matched_lenses = self._match_lenses(listing.title, listing.description or "")
            if matched_lenses:
                lens_names = [l['lens_name'] for l in matched_lenses]
                logger.info(f"Detected lenses in [{listing_id}]: {', '.join(lens_names)}")
                # Store all matched lens IDs in matched_lens_id as comma-separated slugs
                listing.matched_lens_id = ",".join([l['lens_id'] for l in matched_lenses])
                listing.lens_confidence_score = max(l['confidence'] for l in matched_lenses)
                listing.lens_match_method = "camera_text_detection"
            
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
        """Scrape all camera listings from the category/categories."""
        self.initialize()
        
        # Determine which categories to scrape
        if self.category_url:
            categories_to_scrape = [self.category_url]
        else:
            categories_to_scrape = self.CATEGORY_URLS
        
        all_listings = []
        
        for category_url in categories_to_scrape:
            listings = self._scrape_single_category(category_url, max_pages, limit)
            all_listings.extend(listings)
            
            if limit > 0 and len(all_listings) >= limit:
                logger.info(f"Reached global limit: {limit}")
                all_listings = all_listings[:limit]
                break
        
        logger.info(f"Category scrape complete. Total listings: {len(all_listings)}")
        return all_listings
    
    def _scrape_single_category(self, category_path: str, max_pages: int = 0, limit: int = 0) -> List[Listing]:
        """Scrape a single category page."""
        listings = []
        current_url = f"{self.BASE_URL}{category_path}"
        page_count = 0
        total_scraped = 0
        
        logger.info(f"Starting camera category scrape: {current_url}")
        
        while current_url:
            if max_pages > 0 and page_count >= max_pages:
                logger.info(f"Reached max pages limit: {max_pages}")
                break
            
            logger.info(f"Fetching page {page_count + 1}: {current_url}")
            result = self.crawler.fetch(current_url)
            
            if result.error_type != ErrorType.SUCCESS or not result.html:
                logger.error(f"Failed to fetch page: {result.error_msg}")
                break
            
            page_listings = self._parse_listings_page(result.html)
            logger.info(f"Found {len(page_listings)} listings on page {page_count + 1}")
            
            for listing_id, url in page_listings:
                if limit > 0 and total_scraped >= limit:
                    logger.info(f"Reached limit: {limit}")
                    return listings
                
                listing = self.scrape_listing(listing_id, url)
                if listing:
                    listings.append(listing)
                total_scraped += 1
            
            next_url = self._get_next_page_url(result.html, page_count + 1)
            if not next_url:
                logger.info("No more pages to scrape")
                break
            
            current_url = next_url
            page_count += 1
        
        logger.info(f"Category {category_path} complete. Listings: {len(listings)}")
        return listings
    
    def _parse_listings_page(self, html: str) -> List[tuple[str, str]]:
        """Parse a category page to extract listing IDs and URLs."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        
        for tr in soup.find_all('tr'):
            link = tr.find('a', href=re.compile(r'/msg/.*'))
            if link:
                href = link.get('href', '')
                # Match /msg/*/*/*/.../ID.html pattern - capture ID from end
                match = re.search(r'/msg/(?:[^/]+/)*([^/]+)\.html$', href)
                if match:
                    listing_id = match.group(1)
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    listings.append((listing_id, full_url))
        
        return listings
    
    def _get_next_page_url(self, html: str, current_page: int = 1) -> Optional[str]:
        """Extract next page URL from category page."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for page links with pattern /page{N}.html
        page_links = {}
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Match /page{N}.html pattern
            page_match = re.search(r'/page(\d+)\.html', href)
            if page_match:
                page_num = int(page_match.group(1))
                full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                page_links[page_num] = full_url
            # Also check for text-based next buttons
            text = link.get_text(strip=True).lower()
            if text in ['tālāk', 'next', '→', '»', '>>']:
                full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                # Try to extract page number from the URL
                page_match = re.search(r'/page(\d+)\.html', href)
                if page_match:
                    page_links[int(page_match.group(1))] = full_url
                else:
                    # Assume it's the next page
                    return full_url
        
        # Find the lowest page number greater than current_page
        next_pages = [p for p in page_links.keys() if p > current_page]
        if next_pages:
            return page_links[min(next_pages)]
        
        return None
    
    def test_url(self, url: str) -> Optional[Listing]:
        """Test scraping a single URL (for debugging)."""
        match = re.search(r'/msg/[^/]+/[^/]+/[^/]+/([^/]+)\.html', url)
        if match:
            listing_id = match.group(1)
        else:
            listing_id = "test"
        
        return self.scrape_listing(listing_id, url)
    
    def run(self) -> Dict[str, int]:
        """Run the full camera scraping process."""
        self.initialize()
        
        from src.database.repository import ScrapeRunRepository
        
        with get_session() as session:
            run_id = ScrapeRunRepository.create(session, 'camera', {
                'category_path': self.CATEGORY_URL,
                'max_pages': self.config.scraper.max_pages,
                'max_listings': self.config.scraper.max_listings
            })
            session.commit()
        
        try:
            # Scrape listings
            listings = self.scrape_category(
                max_pages=self.config.scraper.max_pages,
                limit=self.config.scraper.max_listings
            )
            
            # Save to database
            if not self.config.scraper.test_mode:
                with get_session() as session:
                    new_count = 0
                    updated_count = 0
                    
                    for listing in listings:
                        try:
                            result = ListingRepository.create_or_update(session, listing, run_id)
                            if result[1] == 'new':
                                new_count += 1
                            elif result[1] == 'updated':
                                updated_count += 1
                            elif result[1] == 'unchanged' and listing.matched_camera_id:
                                self.stats['matched_unchanged'] += 1
                            
                            # Download image if available
                            if listing.image_url and self.image_downloader:
                                local_image_path = self.image_downloader.download_image(
                                    listing.image_url,
                                    listing.listing_id
                                )
                                if local_image_path:
                                    logger.info(f"Image saved locally: {local_image_path}")
                                    ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)
                        except Exception as e:
                            logger.error(f"Error saving listing {listing.listing_id}: {e}")
                            continue
                    
                    session.commit()
                    
                    # Update stats
                    self.stats['new'] = new_count
                    self.stats['updated'] = updated_count
                    
                    # Log final accounting for debugging
                    logger.info(
                        f"Camera scrape accounting: processed={self.stats['processed']}, "
                        f"filtered={self.stats['filtered']}, failed={self.stats['failed']}, "
                        f"matched={self.stats['matched']}, matched_unchanged={self.stats['matched_unchanged']}, "
                        f"passed_filter_unmatched={self.stats['passed_filter_unmatched']}, "
                        f"new={self.stats['new']}, updated={self.stats['updated']}"
                    )
            
            # Complete run
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'completed',
                    'total': self.stats['processed'],
                    'new': self.stats['new'],
                    'updated': self.stats['updated'],
                    'failed': self.stats['failed']
                })
                session.commit()
            
            return self.get_stats()
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'failed',
                    'error': str(e)
                })
                session.commit()
            raise
