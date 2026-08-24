"""Cases/PSU category scraper for ss.com with auto-categorization."""
import re
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

from src.scraper.crawler import Crawler, ErrorType
from src.scraper.base_scraper import BaseScraper
from src.utils.config import AppConfig
from src.utils.text import normalize_text, compute_content_hash
from src.utils.logger import get_logger
from src.utils.image_downloader import ImageDownloader
from src.database.connection import get_session
from src.database.repository import CaseRepository, PSURepository, ListingRepository
from src.scraper.case_matcher import CaseMatcher
from src.scraper.psu_matcher import PSUMatcher
from sqlalchemy import text

logger = get_logger("cases_scraper")


class CasesScraper(BaseScraper):
    """Scraper for Cases/PSU category with auto-categorization."""

    # Keywords that indicate a computer case
    CASE_KEYWORDS = ['korpusu', 'case', 'korpuss']

    def __init__(self, config: AppConfig, crawler: Crawler):
        super().__init__(config, crawler)
        self.parser = CasesParser()

        # Stats tracking
        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'cases': 0,
            'psus': 0
        }

        # Load matchers
        with get_session() as session:
            cases = CaseRepository.get_all(session)
            self.case_matcher = CaseMatcher(cases)

            psus = PSURepository.get_all(session)
            self.psu_matcher = PSUMatcher(psus)

            logger.info(f"Loaded {len(cases)} case and {len(psus)} PSU references")

        # Initialize image downloaders (one per auto-detected category)
        self.case_image_downloader: Optional[ImageDownloader] = None
        self.psu_image_downloader: Optional[ImageDownloader] = None
        self.image_downloader: Optional[ImageDownloader] = None  # backwards compatibility

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
            'cases': 0,
            'psus': 0
        }

    def scrape_category(self) -> List[Dict[str, Any]]:
        """Scrape cases category."""
        # Initialize image downloaders (other init done in __init__)
        self.case_image_downloader = ImageDownloader(base_dir="images/cases")
        self.psu_image_downloader = ImageDownloader(base_dir="images/psu")
        self.image_downloader = self.case_image_downloader  # default

        logger.info(f"Scraping cases category: {self.config.scraper.category_path}")

        listings = []
        page = 1

        while True:
            url = f"{self.config.scraper.base_url}{self.config.scraper.category_path}"
            if page > 1:
                url = f"{url}page{page}.html"

            result = self.crawler.fetch(url)

            if result.error_type != ErrorType.SUCCESS:
                logger.error(f"Failed to fetch page {page}: {result.error_msg}")
                break

            # Parse listing URLs
            listing_urls = self.parser.extract_listing_urls(result.html)
            logger.info(f"Found {len(listing_urls)} listings on page {page}")

            for listing_id, listing_url in listing_urls:
                try:
                    listing = self.scrape_listing(listing_id, listing_url)
                    if listing:
                        # Save to database with version tracking
                        saved = self._save_listing(listing)
                        if saved:
                            listings.append(listing)
                            self.stats['processed'] += 1
                except Exception as e:
                    logger.error(f"Error scraping {listing_id}: {e}")
                    self.stats['failed'] += 1

            # Check for next page
            if not self.parser.has_next_page(result.html):
                break

            page += 1

            if self.config.scraper.max_pages and page > self.config.scraper.max_pages:
                break

        # Deactivate listings that weren't seen in this session (or any recent one).
        # Matches the pattern from engine.py:247 and cpu_scraper.py:236 — the cases
        # scraper was the only secondary scraper missing this step, so any case /
        # PSU row that wasn't found in this run but is older than stale_after_days
        # gets flipped to is_active=false here.
        try:
            with get_session() as session:
                stale_count = ListingRepository.mark_stale(
                    session,
                    days=self.config.scraper.stale_after_days,
                )
                if stale_count:
                    logger.info(
                        f"🗑️ Marked {stale_count} listings as stale "
                        f"(not seen for {self.config.scraper.stale_after_days}+ days)"
                    )
        except Exception as e:
            logger.error(f"mark_stale failed after case scrape: {e}")

        return listings

    def scrape_listing(self, listing_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single listing and categorize as case or PSU."""
        result = self.crawler.fetch(url)

        if result.error_type != ErrorType.SUCCESS:
            logger.warning(f"Failed to fetch {url}: {result.error_msg}")
            self.stats['failed'] += 1
            return None

        # Parse the listing
        listing = self.parser.parse_listing_page(result.html, listing_id, url)

        if not listing:
            self.stats['failed'] += 1
            logger.warning(f"{listing_id}: Failed to parse")
            return None

        # Categorize based on description keywords
        category = self._categorize_listing(listing)
        listing['category'] = category

        # Track category stats
        if category == 'case':
            self.stats['cases'] += 1
        else:
            self.stats['psus'] += 1

        # Match to appropriate reference
        matched = False
        if category == 'case':
            match_result = self.case_matcher.match_listing(
                listing.get('title', '') + ' ' + listing.get('description', ''),
                listing.get('price')
            )
            if match_result.case:
                listing['matched_case_id'] = match_result.case.id
                listing['matched_case_name'] = match_result.case.name
                listing['confidence_score'] = match_result.confidence
                listing['match_method'] = match_result.method
                matched = True
        else:
            match_result = self.psu_matcher.match_listing(
                listing.get('title', '') + ' ' + listing.get('description', ''),
                listing.get('price')
            )
            if match_result.psu:
                listing['matched_psu_id'] = match_result.psu.id
                listing['matched_psu_name'] = match_result.psu.name
                listing['confidence_score'] = match_result.confidence
                listing['match_method'] = match_result.method
                matched = True

        if matched:
            self.stats['matched'] += 1

        # Compute content hash
        listing['content_hash'] = compute_content_hash(
            listing.get('title', ''),
            listing.get('price', 0),
            listing.get('location', '')
        )

        return listing

    def _categorize_listing(self, listing: Dict[str, Any]) -> str:
        """Categorize listing as 'case' or 'psu' based on keywords."""
        text = normalize_text(listing.get('title', '') + ' ' + listing.get('description', ''))

        # Check for case keywords
        for keyword in self.CASE_KEYWORDS:
            if keyword in text:
                return 'case'

        # Default to PSU if no case keywords found
        return 'psu'

    def _save_listing(self, listing: Dict[str, Any]) -> bool:
        """Save listing to database with version tracking."""
        try:
            with get_session() as session:
                existing = session.execute(
                    text("SELECT * FROM listings WHERE listing_id = :id"),
                    {"id": listing['listing_id']}
                ).fetchone()

                if existing:
                    existing_dict = dict(existing._mapping)

                    # Check for changes - convert price_eur to float for comparison
                    existing_price = float(existing_dict['price_eur']) if existing_dict['price_eur'] else 0.0
                    price_changed = abs(existing_price - listing['price']) > 0.01
                    title_changed = existing_dict['title'] != listing['title']
                    desc_changed = existing_dict['description'] != listing['description']
                    loc_changed = existing_dict['seller_location'] != listing['location']

                    has_changes = price_changed or title_changed or desc_changed or loc_changed

                    if has_changes:
                        # Detect what changed
                        changes = []
                        if price_changed:
                            changes.append(f"price €{existing_dict['price_eur']:.2f}→€{listing['price']:.2f}")
                        if title_changed:
                            changes.append("title")
                        if desc_changed:
                            changes.append("description")
                        if loc_changed:
                            changes.append("location")

                        change_str = ", ".join(changes)

                        # Save version history
                        ListingRepository.save_version(session, listing['listing_id'])

                        # Update listing
                        category = listing.get('category', 'case')
                        if category == 'case':
                            session.execute(
                                text("""
                                UPDATE listings
                                SET title = :title,
                                    description = :desc,
                                    price_eur = :price,
                                    seller_location = :location,
                                    date_posted = :date_posted,
                                    matched_case_id = :case_id,
                                    case_confidence_score = :confidence,
                                    case_match_method = :method,
                                    is_active = true,
                                    last_seen_at = NOW(),
                                    updated_at = NOW()
                                WHERE listing_id = :id
                                """),
                                {
                                    "id": listing['listing_id'],
                                    "title": listing['title'],
                                    "desc": listing['description'],
                                    "price": listing['price'],
                                    "location": listing['location'],
                                    "date_posted": listing.get('date_posted'),
                                    "case_id": listing.get('matched_case_id'),
                                    "confidence": listing.get('confidence_score'),
                                    "method": listing.get('match_method')
                                }
                            )
                        else:  # psu
                            session.execute(
                                text("""
                                UPDATE listings
                                SET title = :title,
                                    description = :desc,
                                    price_eur = :price,
                                    seller_location = :location,
                                    matched_psu_id = :psu_id,
                                    psu_confidence_score = :confidence,
                                    psu_match_method = :method,
                                    is_active = true,
                                    last_seen_at = NOW(),
                                    updated_at = NOW()
                                WHERE listing_id = :id
                                """),
                                {
                                    "id": listing['listing_id'],
                                    "title": listing['title'],
                                    "desc": listing['description'],
                                    "price": listing['price'],
                                    "location": listing['location'],
                                    "psu_id": listing.get('matched_psu_id'),
                                    "confidence": listing.get('confidence_score'),
                                    "method": listing.get('match_method')
                                }
                            )

                        self.stats['updated'] += 1
                        emoji = 'CASE' if category == 'case' else 'PSU'
                        match_info = ""
                        if category == 'case' and listing.get('matched_case_id'):
                            match_info = f" -> {listing.get('matched_case_name', 'Case')}"
                        elif category == 'psu' and listing.get('matched_psu_id'):
                            match_info = f" -> {listing.get('matched_psu_name', 'PSU')}"
                        logger.info(f"[UPDATE] {emoji} {listing['listing_id']}{match_info}: Updated ({change_str})")
                    else:
                        # Just update last_seen
                        session.execute(
                            text("UPDATE listings SET last_seen_at = NOW() WHERE listing_id = :id"),
                            {"id": listing['listing_id']}
                        )
                        self.stats['unchanged'] += 1
                        emoji = 'CASE' if listing.get('category') == 'case' else 'PSU'
                        match_info = ""
                        if listing.get('category') == 'case' and listing.get('matched_case_id'):
                            match_info = f" -> {listing.get('matched_case_name', 'Case')}"
                        elif listing.get('category') == 'psu' and listing.get('matched_psu_id'):
                            match_info = f" -> {listing.get('matched_psu_name', 'PSU')}"
                        logger.info(f"[UNCHANGED] {emoji} {listing['listing_id']}{match_info}: Unchanged")
                else:
                    # Insert new
                    category = listing.get('category', 'case')
                    if category == 'case':
                        session.execute(
                            text("""
                            INSERT INTO listings (
                                listing_id, title, description, price_eur, seller_location,
                                listing_url, image_url, category, date_posted,
                                matched_case_id, case_confidence_score, case_match_method,
                                content_hash, is_active
                            ) VALUES (
                                :id, :title, :desc, :price, :location,
                                :url, :image, 'case', :date_posted,
                                :case_id, :confidence, :method,
                                :hash, true
                            )
                            """),
                            {
                                "id": listing['listing_id'],
                                "title": listing['title'],
                                "desc": listing['description'],
                                "price": listing['price'],
                                "location": listing['location'],
                                "url": listing['url'],
                                "image": listing.get('image_url'),
                                "date_posted": listing.get('date_posted'),
                                "case_id": listing.get('matched_case_id'),
                                "confidence": listing.get('confidence_score'),
                                "method": listing.get('match_method'),
                                "hash": listing.get('content_hash')
                            }
                        )
                    else:  # psu
                        session.execute(
                            text("""
                            INSERT INTO listings (
                                listing_id, title, description, price_eur, seller_location,
                                listing_url, image_url, category,
                                matched_psu_id, psu_confidence_score, psu_match_method,
                                content_hash, is_active
                            ) VALUES (
                                :id, :title, :desc, :price, :location,
                                :url, :image, 'psu',
                                :psu_id, :confidence, :method,
                                :hash, true
                            )
                            """),
                            {
                                "id": listing['listing_id'],
                                "title": listing['title'],
                                "desc": listing['description'],
                                "price": listing['price'],
                                "location": listing['location'],
                                "url": listing['url'],
                                "image": listing.get('image_url'),
                                "psu_id": listing.get('matched_psu_id'),
                                "confidence": listing.get('confidence_score'),
                                "method": listing.get('match_method'),
                                "hash": listing.get('content_hash')
                            }
                        )

                    self.stats['new'] += 1
                    emoji = 'CASE' if category == 'case' else 'PSU'
                    match_info = ""
                    if category == 'case' and listing.get('matched_case_id'):
                        match_info = f" -> {listing.get('matched_case_name', 'Case')}"
                    elif category == 'psu' and listing.get('matched_psu_id'):
                        match_info = f" -> {listing.get('matched_psu_name', 'PSU')}"
                    logger.info(f"[NEW] {emoji} {listing['listing_id']}{match_info}: New")

                    # Download image if available
                    image_url = listing.get('image_url')
                    category = listing.get('category', 'case')
                    downloader = self.case_image_downloader if category == 'case' else self.psu_image_downloader
                    if image_url and downloader:
                        local_image_path = downloader.download_image(
                            image_url,
                            listing['listing_id']
                        )
                        if local_image_path:
                            logger.info(f"Image saved locally: {local_image_path}")
                            ListingRepository.update_local_image_path(session, listing['listing_id'], local_image_path)

                session.commit()
                return True

        except Exception as e:
            logger.error(f"[ERROR] Error saving {listing['listing_id']}: {e}")
            self.stats['failed'] += 1
            return False


class CasesParser:
    """Parser for cases/PSU listings."""

    def extract_listing_urls(self, html: str) -> List[tuple]:
        """Extract listing URLs from category page."""
        urls = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find all listing links
        for link in soup.find_all('a', href=re.compile(r'/msg/')):
            href = link.get('href', '')
            if '/msg/' in href:
                match = re.search(r'/([a-z]+)\.html$', href)
                if match:
                    listing_id = match.group(1)
                    full_url = href if href.startswith('http') else f"https://www.ss.com{href}"
                    urls.append((listing_id, full_url))

        return urls

    def has_next_page(self, html: str) -> bool:
        """Check if there's a next page."""
        soup = BeautifulSoup(html, 'html.parser')
        next_link = soup.find('a', {'class': 'a_next'})
        return next_link is not None

    def parse_listing_page(self, html: str, listing_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse a single listing page."""
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
        price = self._extract_price(soup)

        # Extract location
        location = self._extract_location(soup)

        # Extract image - prefer the main 800px gallery image, fall back to the first thumbnail's full-size link.
        image_url = None
        # 1) The gallery's main preview image is usually the largest available (often already 800px).
        main_img = soup.find('img', {'id': 'msg_img_img'})
        if main_img and main_img.get('src'):
            image_url = main_img['src']
        # 2) If the page only has thumbnails, pick the first link whose href contains .800.jpg.
        if not image_url:
            thumb_link = soup.select_one('#tr_foto a[href*=".800.jpg"]')
            if thumb_link and thumb_link.get('href'):
                image_url = thumb_link['href']
        # 3) Last resort: any direct image in the content area.
        if not image_url:
            img_div = soup.find('div', {'id': 'content_sys_div_msg'})
            if img_div:
                img = img_div.find('img')
                if img and img.get('src'):
                    image_url = img['src']

        if image_url and image_url.startswith('/'):
            image_url = f"https://i.ss.com{image_url}"

        # Extract date from footer using shared parser logic
        date_posted = self._extract_date(soup)

        return {
            'listing_id': listing_id,
            'title': title,
            'description': description,
            'price': price,
            'location': location,
            'url': url,
            'image_url': image_url,
            'date_posted': date_posted
        }

    def _extract_date(self, soup):
        """Extract listing date_posted from footer."""
        import datetime
        for td in soup.select('td.msg_footer'):
            text = td.get_text(strip=True)
            # "Datums: DD.MM.YYYY HH:MM"
            match = __import__('re').search(r'Datums:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', text)
            if match:
                day, month, year, hour, minute = match.groups()
                try:
                    return datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
                except ValueError:
                    pass
            # ISO fallback
            match = __import__('re').search(r'(\d{4})-(\d{2})-(\d{2})', text)
            if match:
                year, month, day = match.groups()
                try:
                    return datetime.datetime(int(year), int(month), int(day))
                except ValueError:
                    pass
        return None

    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract price from listing."""
        price_cell = soup.find('td', {'class': 'ads_price'})
        if price_cell:
            price_text = price_cell.get_text(strip=True)
            match = re.search(r'([\d,]+)', price_text.replace(' ', ''))
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    pass
        return 0.0

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract location from listing, ignoring obfuscated phone-number placeholders."""
        # Try the explicit "Vieta:/Место:" row first to avoid phone-number placeholder rows.
        for label_td in soup.find_all('td', {'class': 'ads_contacts_name'}):
            label_text = label_td.get_text(strip=True).lower()
            if 'vieta' in label_text or 'место' in label_text:
                value_td = label_td.find_next_sibling('td', {'class': 'ads_contacts'})
                if value_td:
                    return value_td.get_text(strip=True)

        # Generic contacts cell fallback, but skip phone-number placeholders.
        contacts = soup.find('td', {'class': 'ads_contacts'})
        if contacts:
            text = contacts.get_text(strip=True)
            if 'tālruni' not in text.lower() and 'parādīt' not in text.lower() and not text.startswith('(+371)'):
                return text

        address = soup.find('td', {'class': 'td_address'})
        if address:
            return address.get_text(strip=True)

        return ""
