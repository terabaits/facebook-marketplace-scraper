"""RAM Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, RAMReferenceRepository, ScrapeRunRepository
from src.models.schemas import Listing, RAMReference
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.ram_parser import RAMParser
from src.scraper.ram_matcher import RAMMatcher
from src.utils.config import AppConfig, ScraperConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash
from src.utils.image_downloader import ImageDownloader

logger = get_logger("ram_scraper")


class RAMScraper:
    """Scraper for RAM listings from ss.com"""

    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/computers/completing-pc/ram/"

    def __init__(self, config: AppConfig):
        """Initialize the RAM scraper."""
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.parser = RAMParser()
        self.matcher: Optional[RAMMatcher] = None

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
        """Initialize database and load RAM references."""
        logger.info("Initializing RAM scraper...")

        # Initialize database
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")

        # Load RAM reference data
        with get_session() as session:
            rams = RAMReferenceRepository.get_all(session)
            self.matcher = RAMMatcher(rams)
            logger.info(f"Loaded {len(rams)} RAM references")

            # Initialize image downloader
            self.image_downloader = ImageDownloader(base_dir="images/rams")

    def _extract_frequency_from_text(self, text: str) -> Optional[int]:
        """Extract frequency in MHz from title/description text."""
        if not text:
            return None

        text_lower = text.lower()

        # Look for patterns like "3600mhz", "3600 mhz", "DDR4-3600", "7200mhz"
        patterns = [
            r'(\d{4})\s*mhz',           # 3600mhz, 3600 mhz
            r'ddr\d?-?(\d{4})',         # DDR4-3600, DDR5-7200
            r'\b(\d{4})\s*mhz\b',       # standalone 3600mhz
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                freq = int(match.group(1))
                # Validate reasonable RAM frequencies (400-10000 MHz)
                if 400 <= freq <= 10000:
                    logger.debug(f"Extracted frequency {freq} MHz from text using pattern {pattern}")
                    return freq

        return None

    def _infer_ddr_type(self, freq_mhz: int) -> str:
        """Infer DDR type from frequency."""
        if freq_mhz >= 8000:
            return "DDR5"
        elif freq_mhz >= 4800:
            return "DDR5"
        elif freq_mhz >= 2133:
            return "DDR4"
        elif freq_mhz >= 800:
            return "DDR3"
        elif freq_mhz >= 400:
            return "DDR2"
        return "DDR"

    def _should_skip_listing(self, listing: Listing) -> bool:
        """Skip listings that are clearly new retail stock (not second-hand RAM)."""
        if not listing.description:
            return False
        text = listing.description.lower()
        # New-in-box with warranty phrases
        skip_phrases = [
            "jauna. iepakojumā. garantija - 2 gadi",
            "jauna. iepakojuma. garantija - 2 gadi",
            "jauna iepakojumā garantija 2 gadi",
            "jaunas garantija 2 gadi",
            "garantija 2 gadi",
        ]
        for phrase in skip_phrases:
            if phrase in text:
                logger.info(f"Skipping {listing.listing_id}: contains retail-new phrase '{phrase}'")
                return True
        return False

    def _normalize_location(self, location: str) -> str:
        """Normalize seller location to canonical Latvian form."""
        if not location:
            return location
        loc_lower = location.lower().strip()
        # Canonical city mappings for Russian/Latvian variants
        mappings = {
            'rīga': 'Rīga',
            'рига': 'Rīga',
            'riga': 'Rīga',
            'valmiera un raj.': 'Valmiera un raj.',
            'valmiera': 'Valmiera',
            'валмиера и р-он': 'Valmiera un raj.',
            'валмиера': 'Valmiera',
            'liepāja': 'Liepāja',
            'лиепая': 'Liepāja',
            'daugavpils': 'Daugavpils',
            'даугавпилс': 'Daugavpils',
            'jelgava': 'Jelgava',
            'елгава': 'Jelgava',
            'ventspils': 'Ventspils',
            'вентспилс': 'Ventspils',
            'jūrmala': 'Jūrmala',
            'юрмала': 'Jūrmala',
            'rēzekne': 'Rēzekne',
            'рэзекне': 'Rēzekne',
            'ogre': 'Ogre',
            'огре': 'Ogre',
            'sigulda': 'Sigulda',
            'cēsis': 'Cēsis',
            'даугавпилс': 'Daugavpils',
        }
        return mappings.get(loc_lower, location)

    def _extract_location(self, html: str) -> Optional[str]:
        """Extract seller location from HTML, preferring the Vieta/Pilsēta/Место row."""
        # Look for the explicit location row first (Latvian, Russian, English)
        loc_match = re.search(
            r'<td[^>]*class="ads_contacts_name"[^>]*>\s*(?:Vieta|Pilsēta|Atrašanās vieta|Место|Город|Place|Location|City)\s*:?\s*</td>\s*<td[^>]*class="ads_contacts"[^>]*>([^<]+)</td>',
            html,
            re.IGNORECASE | re.DOTALL
        )
        if loc_match:
            return self._normalize_location(loc_match.group(1).strip())

        # Fallback to any ads_contacts cell
        contacts_match = re.search(r'class="ads_contacts"[^>]*>([^<]+)</td>', html)
        if contacts_match:
            return self._normalize_location(contacts_match.group(1).strip())

        # Older td_address class
        loc_match = re.search(r'class="td_address"[^>]*>([^<]+)</td>', html)
        if loc_match:
            return self._normalize_location(loc_match.group(1).strip())

        return None

    def _extract_speed_from_specs(self, html: str) -> Optional[str]:
        """Extract RAM speed/DDR type from specs table in HTML."""
        # Look for RAM type or frequency in specs
        ram_type_match = re.search(r'Operativas atminas tips[^<]*<[^>]*>[^<]*<[^>]*>([^<]+)', html)
        if ram_type_match:
            return ram_type_match.group(1).strip()

        # Alternative field names
        ram_type_match = re.search(r'Veids[^<]*<[^>]*>[^<]*<[^>]*>([^<]+)', html)
        if ram_type_match:
            return ram_type_match.group(1).strip()

        return None

    def scrape_listing(self, listing_id: str, url: str) -> Optional[Listing]:
        """Scrape a single RAM listing."""
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

            # Skip retail-new listings
            if self._should_skip_listing(listing):
                self.stats['processed'] += 1
                return None

            # Extract location
            location = self._extract_location(result.html)
            if location:
                listing.seller_location = location

            # Extract speed from specs AND title
            extracted_speed = None
            desc_text = listing.description if listing.description else ""
            title_freq = self._extract_frequency_from_text(listing.title + ' ' + desc_text)

            if hasattr(listing, 'ram_type') and listing.ram_type:
                ram_type = listing.ram_type

                # Use frequency from title if available (more accurate)
                if title_freq:
                    ram_type = self._infer_ddr_type(title_freq)
                    extracted_speed = f"{ram_type}-{title_freq}"
                elif hasattr(listing, 'ram_frequency_mhz') and listing.ram_frequency_mhz:
                    freq = listing.ram_frequency_mhz
                    if ram_type == "DDR":
                        ram_type = self._infer_ddr_type(freq)
                    extracted_speed = f"{ram_type}-{freq}"
                else:
                    extracted_speed = ram_type

            # Match to RAM reference - use title + description + extracted fields
            search_text = listing.title
            if listing.description:
                search_text = f"{listing.title} {listing.description}"

            match_result = self.matcher.match_listing(
                search_text,
                listing.capacity_gb,
                extracted_speed,
                getattr(listing, 'ram_manufacturer', None),
                getattr(listing, 'ram_model', None)
            )

            if match_result.ram:
                listing.matched_ram_id = match_result.ram.id
                listing.ram_confidence_score = match_result.confidence
                listing.ram_match_method = match_result.method
                self.stats['matched'] += 1
                logger.info(f"Matched {listing_id}: {match_result.ram.name} "
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
        """Scrape all RAM listings from the category."""
        self.initialize()

        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page = 1
        total_listings = 0
        seen_urls: Set[str] = set()  # Track seen listing URLs across pages

        logger.info(f"Starting RAM scraper from {current_url}")

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

            # Filter out already seen URLs
            new_listings = [(lid, url) for lid, url in listing_urls if url not in seen_urls]
            seen_urls.update(url for _, url in new_listings)

            logger.info(f"Found {len(listing_urls)} listings on page {page}, {len(new_listings)} new")

            for listing_id, url in new_listings:
                if limit > 0 and total_listings >= limit:
                    logger.info(f"Reached global limit ({limit})")
                    return listings

                # Scrape individual listing
                listing = self.scrape_listing(listing_id, url)

                if listing:
                    # Save to database (includes image download)
                    self._save_listing(listing)
                    listings.append(listing)
                    total_listings += 1

                self.stats['processed'] += 1

            # Check for next page
            pagination = self.parser.extract_pagination_info(result.html)
            has_next = pagination.get('has_next', False)
            next_url = pagination.get('next_url')

            if not has_next or not next_url:
                logger.info("No more pages")
                break

            current_url = next_url
            if not current_url.startswith('http'):
                current_url = f"{self.BASE_URL}{current_url}"

            logger.info(f"Next page URL: {current_url}")
            page += 1

        logger.info(f"RAM scraping complete. Stats: {self.stats}")
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
                            text("UPDATE listings SET last_seen_at = NOW() WHERE listing_id = :id"),
                            {"id": listing.listing_id}
                        )
                        self.stats['unchanged'] += 1
                        logger.info(f"⏸️ {listing.listing_id}: Unchanged")
                    else:
                        # Detect what changed
                        changes = []
                        if abs(existing.price_eur - listing.price_eur) > 0.01:
                            changes.append(f"price €{existing.price_eur:.2f}→€{listing.price_eur:.2f}")
                        if existing.title != listing.title:
                            changes.append("title")
                        if existing.description != listing.description:
                            changes.append("description")
                        if existing.seller_location != listing.seller_location:
                            changes.append("location")
                        if existing.matched_ram_id != listing.matched_ram_id:
                            changes.append("match")

                        change_str = ", ".join(changes) if changes else "content"

                        # Save version history BEFORE updating
                        ListingRepository.save_version(session, listing.listing_id)

                        # Update with new data
                        session.execute(
                            text("""
                            UPDATE listings
                            SET title = :title,
                                description = :desc,
                                price_eur = :price,
                                seller_location = :location,
                                matched_ram_id = :ram_id,
                                ram_confidence_score = :confidence,
                                ram_match_method = :method,
                                capacity_gb = :capacity,
                                is_active = true,
                                last_seen_at = NOW(),
                                updated_at = NOW()
                            WHERE listing_id = :id
                            """),
                            {
                                "id": listing.listing_id,
                                "title": listing.title,
                                "desc": listing.description,
                                "price": listing.price_eur,
                                "location": listing.seller_location,
                                "ram_id": listing.matched_ram_id,
                                "confidence": listing.ram_confidence_score,
                                "method": listing.ram_match_method,
                                "capacity": listing.capacity_gb
                            }
                        )

                        self.stats['updated'] += 1
                        
                        # Log with appropriate emoji
                        if listing.ram_confidence_score and listing.ram_confidence_score < self.config.scraper.min_confidence_threshold:
                            logger.warning(f"⚠️ LOW_CONFIDENCE: {listing.listing_id} (confidence {listing.ram_confidence_score:.2%})")
                        else:
                            logger.info(f"💰 {listing.listing_id}: Updated ({change_str})")
                        
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
                    session.execute(
                        text("""
                        INSERT INTO listings (
                            listing_id, title, description, price_eur, seller_location,
                            listing_url, image_url, date_posted, category,
                            matched_ram_id, ram_confidence_score, ram_match_method,
                            capacity_gb, content_hash, is_active
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image, :date, 'ram',
                            :ram_id, :confidence, :method,
                            :capacity, :hash, true
                        )
                        """),
                        {
                            "id": listing.listing_id,
                            "title": listing.title,
                            "desc": listing.description,
                            "price": listing.price_eur,
                            "location": listing.seller_location,
                            "url": listing.listing_url,
                            "image": listing.image_url,
                            "date": listing.date_posted,
                            "ram_id": listing.matched_ram_id,
                            "confidence": listing.ram_confidence_score,
                            "method": listing.ram_match_method,
                            "capacity": listing.capacity_gb,
                            "hash": listing.content_hash
                        }
                    )
                    self.stats['new'] += 1

                    # Log new listing
                    if listing.ram_confidence_score and listing.ram_confidence_score < self.config.scraper.min_confidence_threshold:
                        logger.warning(f"⚠️ LOW_CONFIDENCE: {listing.listing_id} (confidence {listing.ram_confidence_score:.2%})")
                    else:
                        logger.info(f"✨ {listing.listing_id}: New")

                    # Download image if available
                    if listing.image_url and self.image_downloader:
                        local_image_path = self.image_downloader.download_image(
                            listing.image_url,
                            listing.listing_id
                        )
                        if local_image_path:
                            logger.info(f"Image saved locally: {local_image_path}")
                            # Update listing with local image path
                            ListingRepository.update_local_image_path(session, listing.listing_id, local_image_path)

        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")

    def scrape_single(self, url: str) -> Optional[Listing]:
        """Scrape a single RAM listing by URL."""
        self.initialize()

        match = re.search(r'/([a-z]+)\.html$', url)
        if not match:
            logger.error(f"Could not extract listing ID from URL: {url}")
            return None

        listing_id = match.group(1)
        listing = self.scrape_listing(listing_id, url)

        if listing:
            # Save to database (test-url should also save!)
            self._save_listing(listing)

        return listing

    def run(self) -> Dict[str, Any]:
        """Run full RAM scrape."""
        self.scrape_category(
            max_pages=self.config.scraper.max_pages,
            limit=self.config.scraper.max_listings
        )
        return self.stats

    def get_stats(self) -> Dict[str, int]:
        """Get current scrape statistics."""
        return self.stats.copy()
