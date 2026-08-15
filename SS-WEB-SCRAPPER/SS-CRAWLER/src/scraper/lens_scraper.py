"""Lens Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, LensReferenceRepository, ScrapeRunRepository
from src.models.schemas import Listing
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.parser import ListingParser
from src.utils.config import AppConfig, ScraperConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash
from src.utils.image_downloader import ImageDownloader

from sqlalchemy import text

logger = get_logger("lens_scraper")


class LensScraper:
    """Scraper for camera lens listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/photo-optics/objectives/"
    
    # Filter patterns (case insensitive)
    FILTER_BRANDS = ['nikon']
    FILTER_STORES = ['internetveikals']
    FILTER_CONDITION = ['jauns']
    
    def __init__(self, config: AppConfig):
        """Initialize the lens scraper."""
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.lens_references = []
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'filtered': 0
        }
        self.image_downloader: Optional[ImageDownloader] = None
    
    def initialize(self):
        """Initialize database."""
        logger.info("Initializing Lens scraper...")
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load lens references from database
        with get_session() as session:
            self.lens_references = LensReferenceRepository.get_all(session)
            logger.info(f"Loaded {len(self.lens_references)} lens references")
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/lenses")
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/lenses")
    
    def _load_lens_references(self):
        """Load lens reference data from database."""
        with get_session() as session:
            self.lens_references = LensReferenceRepository.get_all(session)
            logger.info(f"Loaded {len(self.lens_references)} lens references from database")
    
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
            'filtered': 0
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
        
        # Check for online stores
        if 'internetveikals' in full_text:
            return True, "filtered_internetveikals"
        
        # Check for "new" condition
        if 'jauns' in full_text:
            return True, "filtered_jauns"
        
        return False, ""
    
    def _extract_location(self, html: str) -> Optional[str]:
        """Extract seller location from HTML."""
        contacts_match = re.search(r'class="ads_contacts"[^>]*>([^<]+)</td>', html)
        if contacts_match:
            return contacts_match.group(1).strip()
        
        loc_match = re.search(r'class="td_address"[^>]*>([^<]+)</td>', html)
        if loc_match:
            return loc_match.group(1).strip()
        
        return None
    
    def _extract_phone(self, html: str) -> Optional[str]:
        """Extract phone number from HTML if available."""
        # Look for phone patterns in the page
        phone_patterns = [
            r'\+371\s*\d[\d\s]*',  # Latvian format
            r'\d{8}',  # 8 digit numbers
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_mount_from_text(self, text: str) -> Optional[str]:
        """Extract camera mount from listing text."""
        text_lower = text.lower()
        
        # Canon mounts - check EF-S first (more specific)
        if 'ef-s' in text_lower or 'efs' in text_lower:
            return 'EF-S'
        if 'canon ef' in text_lower or 'ef mount' in text_lower or 'ef kamer' in text_lower:
            return 'EF'
        # Detect EF from model field like "ef 35" or "ef 24-70"
        if re.search(r'\bef\s+\d', text_lower):
            return 'EF'
        if 'canon rf' in text_lower or 'rf mount' in text_lower:
            return 'RF'
        
        # Sigma specific patterns
        if 'dg dn' in text_lower:
            # DG DN = mirrorless (Sony E, L-mount)
            # But if description mentions Canon, it's likely EF with adapter
            if 'canon' in text_lower:
                return 'EF'
            return 'E'  # Default to Sony E for DG DN
        if 'dg' in text_lower and 'dn' not in text_lower:
            # DG = DSLR (Canon EF, Nikon F)
            if 'canon' in text_lower:
                return 'EF'
            if 'nikon' in text_lower:
                return 'F'
        
        # Sony mounts
        if 'fe' in text_lower or 'sony e' in text_lower or 'e-mount' in text_lower or 'sony' in text_lower:
            return 'E'
        
        # Nikon mounts
        if 'z mount' in text_lower or 'nikon z' in text_lower:
            return 'Z'
        if 'f mount' in text_lower or 'nikon f' in text_lower:
            return 'F'
        
        return None

    def _match_lens(self, title: str, description: str = "") -> tuple[Optional[str], float, str]:
        """
        Match lens listing to reference database.
        Returns (matched_lens_id, confidence_score, match_method)
        """
        
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        full_text = f"{title} {description}".lower()
        
        # Check for "Modelis:" field in the text (ss.com format)
        model_lower = ""
        for line in (title_lower + "\n" + desc_lower).split('\n'):
            if 'modelis:' in line or 'model:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    model_lower = parts[1].strip()
                    logger.info(f"MODEL EXTRACTED: '{model_lower}'")
                    break
        
        # If model not found in labeled fields, check if title contains model info
        if not model_lower:
            title_words = title_lower.split()
            if len(title_words) >= 2:
                potential_model = ' '.join(title_words[1:4])
                if re.search(r'\d+', potential_model):
                    model_lower = potential_model
        
        # Extract brand from title
        detected_brand = None
        if title_lower.startswith('carl zeiss'):
            detected_brand = 'carl zeiss'
        elif title_lower.startswith('leica'):
            detected_brand = 'leica'
        elif title_lower.startswith('fujifilm') or title_lower.startswith('fuji'):
            detected_brand = 'fujifilm'
        else:
            title_words = title.split()
            if title_words:
                detected_brand = title_words[0].lower()
        
        # Validate brand
        known_brands = ['canon', 'nikon', 'sony', 'sigma', 'tamron', 'tokina', 'zeiss', 'leica', 'fujifilm', 'panasonic', 'olympus', 'carl zeiss', 'viltrox']
        if detected_brand not in known_brands:
            for brand in known_brands:
                if brand in full_text:
                    detected_brand = brand
                    break
        
        logger.debug(f"Detected brand: {detected_brand}")
        
        # Detect mount
        detected_mount = self._extract_mount_from_text(full_text)
        logger.info(f"MOUNT DETECT: {detected_mount}")
        
        # Extract focal length
        detected_focal_min = None
        detected_focal_max = None
        focal_from_model = False
        
        if model_lower:
            zoom_match = re.search(r'(\d+)\s*-\s*(\d+)\s*(?:mm)?', model_lower)
            if zoom_match:
                detected_focal_min = int(zoom_match.group(1))
                detected_focal_max = int(zoom_match.group(2))
                focal_from_model = True
            else:
                # Try standalone focal length with mm first, then without mm
                prime_match = re.search(r'\b(\d+)\s*mm\b', model_lower)
                if not prime_match:
                    # For formats like "ef 24 1.4" or "ef 85 f1.8" - extract first number that's likely focal
                    prime_match = re.search(r'\b(\d{2,3})\b', model_lower)  # 2-3 digit numbers are usually focal
                if prime_match:
                    detected_focal_min = int(prime_match.group(1))
                    focal_from_model = True
        
        if detected_focal_min is None:
            zoom_match = re.search(r'(\d+)\s*-\s*(\d+)\s*(?:mm)?', title_lower)
            if zoom_match:
                detected_focal_min = int(zoom_match.group(1))
                detected_focal_max = int(zoom_match.group(2))
            else:
                prime_match = re.search(r'\b(\d+)\s*mm\b', title_lower)
                if prime_match:
                    detected_focal_min = int(prime_match.group(1))
        
        if detected_focal_min is None:
            zoom_match = re.search(r'(\d+)\s*-\s*(\d+)\s*(?:mm)?', full_text)
            if zoom_match:
                detected_focal_min = int(zoom_match.group(1))
                detected_focal_max = int(zoom_match.group(2))
        
        if detected_focal_min:
            logger.info(f"Detected focal: {detected_focal_min}mm{f'-{detected_focal_max}mm' if detected_focal_max else ''} (from_model={focal_from_model})")
        
        # When focal comes from model, only use title for matching (not description)
        # This prevents description mentions of other lenses from confusing the matcher
        if focal_from_model:
            match_text = title_lower
            logger.info(f"Using TITLE ONLY for matching: '{title_lower[:60]}...'")
        else:
            match_text = full_text
        
        best_match = None
        best_score = 0.0
        best_method = "none"
        
        for lens in self.lens_references:
            score = 0.0
            
            brand = lens.get('brand', '').lower()
            lens_name = lens.get('lens_name', '').lower()
            focal_min = lens.get('focal_length_mm')
            focal_max = lens.get('max_focal_length_mm')
            mount = lens.get('mount', '').upper()
            
            if not lens_name:
                continue
            
            # BRAND
            if detected_brand and brand:
                if detected_brand == brand:
                    score += 0.4
                elif detected_brand in brand or brand in detected_brand:
                    score += 0.2
            elif brand and brand in match_text:
                score += 0.15
            
            # FOCAL - when focal comes from model, prioritize exact matches heavily
            focal_score = 0
            if detected_focal_min and detected_focal_max:
                # Zoom lens detected
                if focal_min == detected_focal_min and focal_max == detected_focal_max:
                    # Exact zoom match - very high score, especially when from model
                    focal_score = 0.65 if focal_from_model else 0.35
                elif focal_min == detected_focal_min:
                    focal_score = 0.15
                elif focal_max == detected_focal_max:
                    focal_score = 0.15
                elif focal_min and not focal_max and focal_min == detected_focal_max:
                    focal_score = -0.3
            elif detected_focal_min and not detected_focal_max:
                # Prime lens detected
                if focal_min == detected_focal_min and not focal_max:
                    # Exact prime match - very high score when from model
                    focal_score = 0.65 if focal_from_model else 0.35
                elif focal_min and not focal_max and focal_min == detected_focal_min:
                    focal_score = 0.35
                elif focal_min == detected_focal_min:
                    focal_score = 0.1
                elif focal_max == detected_focal_min:
                    focal_score = 0.1
            else:
                # No zoom range detected in listing
                if focal_min:
                    focal_str = str(focal_min)
                    focal_pattern = rf'{re.escape(focal_str)}(?:\s*mm)?\b'
                    if re.search(focal_pattern, match_text):
                        focal_score = 0.2
            
            score += focal_score
            
            # APERTURE (only if focal_from_model is False, or if aperture found in title)
            max_aperture = lens.get('max_aperture', '')
            if max_aperture:
                aperture_clean = str(max_aperture).replace('f/', '').replace('f', '').strip()
                aperture_major = aperture_clean.split('.')[0].split(',')[0]
                aperture_minor = None
                if '.' in aperture_clean:
                    aperture_minor = aperture_clean.split('.')[1]
                elif ',' in aperture_clean:
                    aperture_minor = aperture_clean.split(',')[1]
                
                # Only match aperture if focal didn't come from model, OR aperture is in title
                # Pattern matches f/number, f number, 1:number, or standalone number comma/point number
                check_aperture = not focal_from_model or bool(re.search(r'(?:^|\s)[fF][/\s]?\d|1:\s*\d|\d\s*[.,]\s*\d', title_lower))
                
                if check_aperture:
                    if aperture_minor:
                        aperture_val = f"{aperture_major}.{aperture_minor}"
                        aperture_patterns = [
                            rf'f\s*[\/\s]{{1,2}}{re.escape(aperture_major)}[.,\s]{{0,2}}{re.escape(aperture_minor)}\b',
                            rf'[\/\s]{re.escape(aperture_major)}[.,\s]{{0,2}}{re.escape(aperture_minor)}\b',
                            rf'f{re.escape(aperture_major)}[.,]\s*{re.escape(aperture_minor)}\b',  # Handle "1, 4"
                            rf'1:\s*{re.escape(aperture_val)}\b',
                            rf'\s+{re.escape(aperture_major)}[.,\s]{{0,2}}{re.escape(aperture_minor)}(?:l|is|usm|\s|$)',
                        ]
                        for pattern in aperture_patterns:
                            if re.search(pattern, match_text, re.IGNORECASE):
                                score += 0.15
                                break
                    else:
                        aperture_patterns = [
                            rf'f[/\s]{{1,2}}{re.escape(aperture_major)}\b',
                            rf'1:\s*{re.escape(aperture_major)}\b',
                            rf'1:\s*{re.escape(aperture_major)}[.,]\d+',
                            rf'\sf{re.escape(aperture_major)}\b',
                            rf'f{re.escape(aperture_major)}(?:l|is|usm|\s|$)',
                        ]
                        for pattern in aperture_patterns:
                            if re.search(pattern, match_text, re.IGNORECASE):
                                score += 0.15
                                break
            
            # GENERATION
            lens_upper = lens_name.upper()
            lens_is_gen2 = re.search(r'\bII\b|\bII[,/\s]|[-/]II\b', lens_upper) is not None
            lens_is_gen3 = re.search(r'\bIII\b|\bIII[,/\s]|[-/]III\b', lens_upper) is not None
            
            model_has_gen_info = ' ii' in model_lower or 'mark ii' in model_lower or 'ii usm' in model_lower or \
                                 ' iii' in model_lower or 'mark iii' in model_lower or 'iii usm' in model_lower
            model_has_gen2 = ' ii' in model_lower or 'mark ii' in model_lower or 'ii usm' in model_lower or model_lower.endswith('ii')
            model_has_gen3 = ' iii' in model_lower or 'mark iii' in model_lower or 'iii usm' in model_lower or model_lower.endswith('iii')
            
            title_has_gen2 = ' ii ' in title_lower or ' mark ii' in title_lower or title_lower.endswith(' ii') or title_lower.endswith('ii') or 'gm ii' in title_lower or 'lii' in title_lower
            title_has_gen3 = ' iii ' in title_lower or ' mark iii' in title_lower or title_lower.endswith(' iii') or title_lower.endswith('iii')
            
            desc_has_gen2 = ' ii ' in desc_lower or ' mark ii' in desc_lower or desc_lower.endswith(' ii') or 'gm ii' in desc_lower
            desc_has_gen3 = ' iii ' in desc_lower or ' mark iii' in desc_lower or desc_lower.endswith(' iii')
            
            if model_has_gen_info:
                listing_mentions_gen2 = model_has_gen2
                listing_mentions_gen3 = model_has_gen3
            elif title_has_gen2 or title_has_gen3:
                listing_mentions_gen2 = title_has_gen2
                listing_mentions_gen3 = title_has_gen3
            elif desc_has_gen2 or desc_has_gen3:
                desc_lens_match = False
                if focal_min and focal_max:
                    focal_pattern = rf'{focal_min}.{{0,10}}{focal_max}'
                    if re.search(focal_pattern, desc_lower):
                        desc_lens_match = True
                
                if desc_lens_match:
                    listing_mentions_gen2 = desc_has_gen2
                    listing_mentions_gen3 = desc_has_gen3
                else:
                    listing_mentions_gen2 = False
                    listing_mentions_gen3 = False
            else:
                listing_mentions_gen2 = False
                listing_mentions_gen3 = False
            
            if lens_is_gen2:
                if listing_mentions_gen2:
                    score += 0.25
                else:
                    score -= 0.5
            else:
                if listing_mentions_gen2:
                    score -= 0.5
                else:
                    score += 0.15
            
            if lens_is_gen3:
                if listing_mentions_gen3:
                    score += 0.25
                else:
                    score -= 0.5
            else:
                if listing_mentions_gen3:
                    score -= 0.5
                else:
                    score += 0.05
            
            # FEATURES (STM, USM, IS, L-series)
            if 'STM' in lens_upper and 'stm' in match_text:
                score += 0.1
            if 'USM' in lens_upper and 'usm' in match_text:
                score += 0.1
            
            # L-series bonus - check both title and description
            lens_is_l_series = 'L ' in lens.get('lens_name', '') or 'L-' in lens.get('lens_name', '')
            if lens_is_l_series:
                if ' l ' in title_lower or ' l-' in title_lower or title_lower.endswith(' l') or title_lower.startswith('l '):
                    score += 0.1
                elif focal_from_model and (' l ' in desc_lower or ' l-series' in desc_lower or 'luxury' in desc_lower):
                    # When focal comes from model, also check description for L-series indicators
                    score += 0.1
            
            if 'IS' in lens_upper:
                is_patterns = [
                    r'\bis\s+usm\b',
                    r'f/\d+\.?\d*l?\s+is\b',
                    r'\(\s*is\s*\)',
                    r'\s+is\s+(?:usm|stm|ii|iii|\d)',
                ]
                for pattern in is_patterns:
                    if re.search(pattern, match_text, re.IGNORECASE):
                        score += 0.1
                        break
            
            # MOUNT MATCHING
            if mount and detected_mount:
                if mount == detected_mount:
                    score += 0.1
                elif detected_mount == 'EF-S' and mount == 'EF':
                    score -= 0.05
                elif detected_mount == 'EF' and mount == 'EF-S':
                    score -= 0.25
                else:
                    score -= 0.15
            
            # EXACT NAME MATCH
            if lens_name in match_text:
                score += 0.25
                best_method = "exact_name"
            
            # Update best match
            if score > best_score:
                best_score = score
                best_match = lens
            elif score == best_score:
                if focal_min == detected_focal_min and focal_max == detected_focal_max:
                    if best_match:
                        best_focal_min = best_match.get('focal_length_mm')
                        best_focal_max = best_match.get('max_focal_length_mm')
                        if not (best_focal_min == detected_focal_min and best_focal_max == detected_focal_max):
                            best_match = lens
                    else:
                        best_match = lens
        
        if best_match and best_score >= 0.5:
            lens_id = f"{best_match.get('brand', '')}_{best_match.get('lens_name', '')}".replace(' ', '_').replace('/', '_')
            method = best_method if best_method != "none" else "fuzzy_match"
            logger.info(f"BEST MATCH: {best_match.get('lens_name')} score={best_score:.2f}")
            return lens_id, min(best_score, 1.0), method
        
        return None, 0.0, "none"
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single lens listing."""
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
            model_has_focal = model and re.search(r'\d+\s*(?:mm)?|\d+-\d+', model) is not None
            
            if brand:
                title_parts.append(brand)
            if model and model != brand:
                title_parts.append(f"Modelis: {model}")
            
            if desc and not model_has_focal:
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
            listing.category = 'lens'
            
            location = self._extract_location(result.html)
            if location:
                listing.seller_location = location
            
            should_filter, filter_reason = self._should_filter(listing.title, listing.description or "")
            if should_filter:
                logger.info(f"Filtered [{listing_id}]: {filter_reason}")
                self.stats['filtered'] += 1
                return None
            
            matched_id, confidence, method = self._match_lens(listing.title, listing.description or "")
            if matched_id:
                listing.matched_lens_id = matched_id
                listing.lens_confidence_score = confidence
                listing.lens_match_method = method
                self.stats['matched'] += 1
                logger.info(f"Matched [{listing_id}]: {matched_id} ({confidence:.0%} confidence)")
            else:
                listing.matched_lens_id = None
                listing.lens_confidence_score = 0.0
                listing.lens_match_method = "none"
                logger.info(f"No match for [{listing_id}]")
            
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
        """Scrape all lens listings from the category."""
        self.initialize()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page_count = 0
        total_scraped = 0
        
        logger.info(f"Starting lens category scrape: {current_url}")
        
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
                    logger.info(f"Reached global limit: {limit}")
                    return listings
                
                listing = self.scrape_listing(listing_id, url)
                if listing:
                    # Save listing and download image inside session
                    self._save_listing(listing)
                    listings.append(listing)
                total_scraped += 1
            
            next_url = self._get_next_page_url(result.html, page_count + 1)
            if not next_url:
                logger.info("No more pages to scrape")
                break
            
            current_url = next_url
            page_count += 1
        
        logger.info(f"Category scrape complete. Total listings: {len(listings)}")
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
        import re
        
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
    
    def _save_listing(self, listing: Listing):
        """Save listing to database with image download."""
        try:
            with get_session() as session:
                existing = session.execute(
                    text("SELECT * FROM listings WHERE listing_id = :id AND category = 'lens'"),
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
                                seller_location = :location, matched_lens_id = :lens_id,
                                lens_confidence_score = :confidence,
                                lens_match_method = :method,
                                is_active = true, last_seen_at = NOW(), updated_at = NOW()
                            WHERE listing_id = :id
                        """), {
                            "id": listing.listing_id,
                            "title": listing.title,
                            "desc": listing.description,
                            "price": listing.price_eur,
                            "location": listing.seller_location,
                            "lens_id": getattr(listing, 'matched_lens_id', None),
                            "confidence": getattr(listing, 'lens_confidence_score', None),
                            "method": getattr(listing, 'lens_match_method', None)
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
                            matched_lens_id, lens_confidence_score, lens_match_method,
                            content_hash, is_active
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image, NOW(), 'lens',
                            :lens_id, :confidence, :method,
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
                        "lens_id": getattr(listing, 'matched_lens_id', None),
                        "confidence": getattr(listing, 'lens_confidence_score', None),
                        "method": getattr(listing, 'lens_match_method', None),
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
    
    def test_url(self, url: str) -> Optional[Listing]:
        """Test scraping a single URL (for debugging)."""
        match = re.search(r'/msg/[^/]+/[^/]+/[^/]+/([^/]+)\.html', url)
        if match:
            listing_id = match.group(1)
        else:
            listing_id = "test"
        
        return self.scrape_listing(listing_id, url)
