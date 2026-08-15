"""SSD Scraper for ss.com"""
import re
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.database.repository import ListingRepository, SSDReferenceRepository, ScrapeRunRepository
from src.models.schemas import Listing, SSDReference
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.ssd_parser import SSDParser
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import AppConfig, ScraperConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash
from src.utils.image_downloader import ImageDownloader

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

        # Listings whose description contains any of these snippets are skipped.
        self.skip_snippets = [
            '<tbody><tr><td>P.-Pt.</td><td>10:00 - 18:00</td></tr></tbody>',
            'Nodrošina ātru datu pārraidi',
            'Startējiet sistēmu dažu sekunžu laikā',
            'Jauns',
        ]

        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'skipped': 0
        }
        self.image_downloader: Optional[ImageDownloader] = None

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

            # Initialize image downloader
            self.image_downloader = ImageDownloader(base_dir="images/ssds")

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
            'skipped': 0
        }

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

    def _should_skip(self, listing: Listing, html: str = "") -> bool:
        """Check if listing should be skipped based on raw HTML or description snippets."""
        description = listing.description or ""
        for snippet in self.skip_snippets:
            if snippet in description or snippet in html:
                logger.warning(f"Skipping {listing.listing_id}: contains forbidden snippet")
                return True
            # Also match a whitespace-normalized version of the snippet in case the page
            # has extra spaces/newlines between tags.
            normalized_snippet = " ".join(snippet.split())
            normalized_html = " ".join(html.split())
            if normalized_snippet in normalized_html:
                logger.warning(f"Skipping {listing.listing_id}: contains forbidden snippet (normalized)")
                return True
        return False

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

            # Skip listings containing forbidden code snippets
            if self._should_skip(listing, result.html):
                self.stats['skipped'] += 1
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
                listing.ssd_match_method = match_result.method[:50] if match_result.method else match_result.method
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
        seen_urls = set()  # Track seen listing URLs across pages

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

        logger.info(f"SSD scraping complete. Stats: {self.stats}")
        return listings

    def _save_listing(self, listing: Listing, download_image: bool = True):
        """Save listing to database."""

        def _image_needs_download(existing_path: Optional[str]) -> bool:
            if not existing_path:
                return True
            full = self.image_downloader.base_dir.parent / existing_path.replace('/', '\\')
            try:
                return not full.exists() or full.stat().st_size < 100
            except Exception:
                return True

        def _download_image(image_url: str, listing_id: str) -> Optional[str]:
            """Download image. Caller decides whether a new download is needed."""
            if not download_image or not image_url or not self.image_downloader:
                return None
            local_path = self.image_downloader.download_image(image_url, listing_id)
            if local_path:
                logger.info(f"Image saved locally: {local_path}")
                ok = ListingRepository.update_local_image_path(session, listing_id, local_path)
                logger.info(f"Updated local_image_path in DB: {ok}")
                return local_path
            logger.warning(f"Image download returned None for {listing_id}: {image_url}")
            return None

        def _existing_image_valid(existing_path: Optional[str]) -> bool:
            if not existing_path:
                return False
            full = self.image_downloader.base_dir.parent / existing_path.replace('/', '\\')
            try:
                return full.exists() and full.stat().st_size >= 100
            except Exception:
                return False

        try:
            with get_session() as session:
                existing = ListingRepository.get_by_id(session, listing.listing_id)
                local_image_path: Optional[str] = None
                image_url_changed = False

                if existing:
                    image_url_changed = bool(listing.image_url and existing.image_url != listing.image_url)

                    if existing.content_hash == listing.content_hash:
                        # Just update last_seen, but also backfill date_posted if missing
                        if existing.date_posted is None and listing.date_posted is not None:
                            session.execute(
                                text("""UPDATE listings SET date_posted = :date, last_seen_at = NOW(), is_active = true WHERE listing_id = :id"""),
                                {"id": listing.listing_id, "date": listing.date_posted}
                            )
                            self.stats['updated'] += 1
                            logger.info(f"🔄 {listing.listing_id}: Backfilled date_posted")
                        else:
                            session.execute(
                                text("""UPDATE listings SET last_seen_at = NOW(), is_active = true WHERE listing_id = :id"""),
                                {"id": listing.listing_id}
                            )
                            self.stats['unchanged'] += 1
                            logger.info(f"⏸️ {listing.listing_id}: Unchanged")

                        # Always backfill/upgrade image_url for ss.com gallery URLs:
                        # .t.jpg -> .800.jpg (full size) so newly parsed listings use the best URL.
                        upgraded = False
                        if listing.image_url and existing.image_url != listing.image_url:
                            existing_is_thumb = '/i.ss.com/gallery/' in (existing.image_url or '') and (existing.image_url or '').endswith('.t.jpg')
                            new_is_full = '/i.ss.com/gallery/' in listing.image_url and listing.image_url.endswith('.800.jpg')
                            if existing_is_thumb and new_is_full:
                                session.execute(
                                    text("UPDATE listings SET image_url = :img WHERE listing_id = :id"),
                                    {"id": listing.listing_id, "img": listing.image_url}
                                )
                                upgraded = True
                                image_url_changed = True
                                logger.info(f"🔄 {listing.listing_id}: Upgraded image_url {existing.image_url} -> {listing.image_url}")

                        # Re-download if URL was upgraded or existing image is missing/undersized
                        if upgraded or not _existing_image_valid(existing.local_image_path):
                            local_image_path = _download_image(listing.image_url, listing.listing_id) or existing.local_image_path
                        else:
                            local_image_path = existing.local_image_path
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
                        if existing.matched_ssd_id != listing.matched_ssd_id:
                            changes.append("match")

                        change_str = ", ".join(changes) if changes else "content"

                        # Save price history (even if price didn't change, to track other changes)
                        session.execute(
                            text("""
                            INSERT INTO price_history (listing_id, price_eur, recorded_at, change_type)
                            VALUES (:id, :price, NOW(), :change_type)
                            """),
                            {
                                "id": listing.listing_id,
                                "price": listing.price_eur,
                                "change_type": change_str[:50]  # Truncate if needed
                            }
                        )

                        # Save version history BEFORE updating (automated)
                        ListingRepository.save_version(session, listing.listing_id)

                        # Update with new data
                        session.execute(
                            text("""
                            UPDATE listings
                            SET title = :title,
                                description = :desc,
                                price_eur = :price,
                                seller_location = :location,
                                image_url = :image,
                                date_posted = :date,
                                matched_ssd_id = :ssd_id,
                                ssd_confidence_score = :confidence,
                                ssd_match_method = :method,
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
                                "image": listing.image_url,
                                "date": listing.date_posted,
                                "ssd_id": listing.matched_ssd_id,
                                "confidence": listing.ssd_confidence_score,
                                "method": (listing.ssd_match_method or "")[:50],
                                "capacity": listing.capacity_gb
                            }
                        )
                        self.stats['updated'] += 1
                        logger.info(f"🔄 {listing.listing_id}: Updated ({change_str})")

                        # Re-download image if URL changed or existing image is missing/undersized
                        if image_url_changed or not _existing_image_valid(existing.local_image_path):
                            local_image_path = _download_image(listing.image_url, listing.listing_id) or existing.local_image_path
                        else:
                            local_image_path = existing.local_image_path
                else:
                    # Insert new
                    session.execute(
                        text("""
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
                            "ssd_id": listing.matched_ssd_id,
                            "confidence": listing.ssd_confidence_score,
                            "method": (listing.ssd_match_method or "")[:50],
                            "capacity": listing.capacity_gb,
                            "hash": listing.content_hash
                        }
                    )
                    self.stats['new'] += 1
                    logger.info(f"✅ {listing.listing_id}: New")

                    # Download image for new listings
                    local_image_path = _download_image(listing.image_url, listing.listing_id)

                # Update the in-memory listing for callers
                if local_image_path:
                    listing.local_image_path = local_image_path
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
        listing = self.scrape_listing(listing_id, url)

        if listing:
            # Save to database (test-url should also save!)
            self._save_listing(listing)

        return listing

    def run(self) -> Dict[str, Any]:
        """Run full SSD scrape."""
        self.scrape_category(
            max_pages=self.config.scraper.max_pages,
            limit=self.config.scraper.max_listings
        )
        return self.stats
