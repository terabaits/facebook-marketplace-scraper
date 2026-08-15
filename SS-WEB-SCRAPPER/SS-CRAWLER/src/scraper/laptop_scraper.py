"""Laptop category scraper for ss.com.

Collects raw laptop listings into `laptop_listings`.
Mobile CPU/GPU reference tables do not exist yet, so this scraper only extracts
structured fields from the SS.com options table and free-text GPU/RAM/storage
hints from the description. Matching will be added later when reference data is
built.
"""
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

from src.scraper.crawler import Crawler, ErrorType
from src.scraper.base_scraper import BaseScraper
from src.scraper.laptop_reference_resolver import LaptopReferenceResolver
from src.scraper.cpu_reference_resolver import CPUReferenceResolver
from src.utils.config import AppConfig
from src.utils.text import normalize_text, compute_content_hash
from src.utils.logger import get_logger
from src.utils.image_downloader import ImageDownloader
from src.database.connection import get_session
from src.database.repository import ListingRepository
from sqlalchemy import text

logger = get_logger("laptop_scraper")


class LaptopScraper(BaseScraper):
    """Scraper for the ss.com laptops / noutbooks category."""

    CATEGORY_PATH = "/lv/electronics/computers/noutbooks/"

    def __init__(self, config: AppConfig, crawler: Crawler):
        super().__init__(config, crawler)
        self.parser = LaptopParser()

        self.stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
        }

        self.image_downloader = ImageDownloader(base_dir="images/laptops")

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
        }

    def scrape_category(self, max_pages: int = 5, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape laptop category pages."""
        logger.info(f"Scraping laptop category: {self.CATEGORY_PATH}")

        listings: List[Dict[str, Any]] = []
        page = 1

        while True:
            url = f"{self.config.scraper.base_url}{self.CATEGORY_PATH}"
            if page > 1:
                url = f"{url}page{page}.html"

            result = self.crawler.fetch(url)

            if result.error_type != ErrorType.SUCCESS:
                logger.error(f"Failed to fetch page {page}: {result.error_msg}")
                break

            listing_urls = self.parser.extract_listing_urls(result.html)
            logger.info(f"Found {len(listing_urls)} laptop listings on page {page}")

            for listing_id, listing_url in listing_urls:
                if limit > 0 and len(listings) >= limit:
                    logger.info(f"Listing limit reached: {limit}")
                    return listings

                try:
                    listing = self.scrape_listing(listing_id, listing_url)
                    if listing:
                        saved = self._save_listing(listing)
                        if saved:
                            listings.append(listing)
                            self.stats['processed'] += 1
                except Exception as e:
                    logger.error(f"Error scraping {listing_id}: {e}")
                    self.stats['failed'] += 1

            if not self.parser.has_next_page(result.html, page):
                break

            page += 1
            if max_pages and page > max_pages:
                logger.info(f"Max pages reached: {max_pages}")
                break

        return listings

    def scrape_listing(self, listing_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single laptop listing page."""
        result = self.crawler.fetch(url)

        if result.error_type != ErrorType.SUCCESS:
            logger.warning(f"Failed to fetch {url}: {result.error_msg}")
            self.stats['failed'] += 1
            return None

        listing = self.parser.parse_listing_page(result.html, listing_id, url)

        if not listing:
            self.stats['failed'] += 1
            logger.warning(f"{listing_id}: Failed to parse")
            return None

        listing['content_hash'] = compute_content_hash(
            listing.get('title', ''),
            listing.get('price', 0),
            listing.get('location', '')
        )

        return listing

    def _save_listing(self, listing: Dict[str, Any]) -> bool:
        """Save laptop listing to `laptop_listings` with versioning."""
        try:
            with get_session() as session:
                resolver = LaptopReferenceResolver(session)
                ref_id, _ref_key = resolver.resolve(
                    listing.get('brand'),
                    listing.get('model'),
                    listing.get('display_size'),
                    listing.get('description'),
                )
                cpu_resolver = CPUReferenceResolver(session)
                cpu_ref_id, _cpu_key, _cpu_model = cpu_resolver.resolve(
                    listing.get('cpu_raw'),
                    listing.get('description'),
                )

                existing = session.execute(
                    text("SELECT * FROM laptop_listings WHERE listing_id = :id"),
                    {"id": listing['listing_id']}
                ).fetchone()

                if existing:
                    existing_dict = dict(existing._mapping)
                    existing_price = float(existing_dict['price_eur']) if existing_dict['price_eur'] else 0.0
                    price_changed = abs(existing_price - listing['price']) > 0.01
                    title_changed = existing_dict['title'] != listing['title']
                    desc_changed = existing_dict['description'] != listing['description']
                    loc_changed = existing_dict['seller_location'] != listing['location']
                    cpu_changed = existing_dict.get('cpu_raw') != listing.get('cpu_raw')
                    gpu_changed = existing_dict.get('gpu_raw') != listing.get('gpu_raw')
                    ram_changed = existing_dict.get('ram_gb') != listing.get('ram_gb')
                    storage_changed = existing_dict.get('storage_gb') != listing.get('storage_gb')
                    storage_type_changed = existing_dict.get('storage_type') != listing.get('storage_type')
                    brand_changed = existing_dict.get('brand') != listing.get('brand')
                    model_changed = existing_dict.get('model') != listing.get('model')
                    display_changed = existing_dict.get('display_size') != listing.get('display_size')
                    condition_changed = existing_dict.get('condition_state') != listing.get('condition_state')
                    seller_type_changed = existing_dict.get('seller_type') != listing.get('seller_type')

                    has_changes = (
                        price_changed or title_changed or desc_changed or loc_changed or
                        cpu_changed or gpu_changed or ram_changed or storage_changed or
                        storage_type_changed or brand_changed or model_changed or
                        display_changed or condition_changed or seller_type_changed
                    )

                    if has_changes:
                        changes = []
                        if price_changed:
                            changes.append(f"price €{existing_dict['price_eur']:.2f}→€{listing['price']:.2f}")
                        if title_changed:
                            changes.append("title")
                        if desc_changed:
                            changes.append("description")
                        if cpu_changed:
                            changes.append(f"cpu {existing_dict.get('cpu_raw')}→{listing.get('cpu_raw')}")
                        if gpu_changed:
                            changes.append(f"gpu {existing_dict.get('gpu_raw')}→{listing.get('gpu_raw')}")
                        if ram_changed:
                            changes.append(f"ram {existing_dict.get('ram_gb')}→{listing.get('ram_gb')}")
                        if storage_changed:
                            changes.append(f"storage {existing_dict.get('storage_gb')}→{listing.get('storage_gb')}")
                        if storage_type_changed:
                            changes.append(f"storage_type {existing_dict.get('storage_type')}→{listing.get('storage_type')}")
                        if brand_changed:
                            changes.append("brand")
                        if model_changed:
                            changes.append("model")
                        if display_changed:
                            changes.append("display")
                        if condition_changed:
                            changes.append("condition")
                        if seller_type_changed:
                            changes.append(f"seller {existing_dict.get('seller_type')}→{listing.get('seller_type')}")

                        change_str = ", ".join(changes)

                        # `listing_versions` FK references the generic `listings` table, not
                        # `laptop_listings`, so versioning would fail. Skip for laptops.
                        # self._save_version(session, listing['listing_id'])

                        session.execute(
                            text("""
                            UPDATE laptop_listings
                            SET title = :title,
                                description = :desc,
                                price_eur = :price,
                                seller_location = :location,
                                date_posted = :date_posted,
                                image_url = :image_url,
                                brand = :brand,
                                model = :model,
                                display_size = :display_size,
                                cpu_raw = :cpu_raw,
                                cpu_freq_ghz = :cpu_freq_ghz,
                                ram_gb = :ram_gb,
                                storage_gb = :storage_gb,
                                storage_type = :storage_type,
                                gpu_raw = :gpu_raw,
                                seller_type = :seller_type,
                                condition_state = :condition_state,
                                content_hash = :content_hash,
                                laptop_reference_id = :laptop_reference_id,
                                cpu_reference_id = :cpu_reference_id,
                                is_active = true,
                                last_seen_at = NOW(),
                                updated_at = NOW()
                            WHERE listing_id = :id
                            """),
                            {
                                **self._db_params(listing),
                                "laptop_reference_id": ref_id,
                                "cpu_reference_id": cpu_ref_id,
                            }
                        )

                        session.execute(
                            text("""
                            INSERT INTO laptop_price_history (listing_id, price_eur, change_type)
                            VALUES (:id, :price, :change_type)
                            """),
                            {
                                "id": listing['listing_id'],
                                "price": listing['price'],
                                "change_type": change_str
                            }
                        )

                        self.stats['updated'] += 1
                        logger.info(f"[UPDATE] LAPTOP {listing['listing_id']}: {change_str}")
                    else:
                        session.execute(
                            text("""
                            UPDATE laptop_listings
                            SET last_seen_at = NOW(), is_active = true
                            WHERE listing_id = :id
                            """),
                            {"id": listing['listing_id']}
                        )
                        self.stats['unchanged'] += 1
                        logger.info(f"[UNCHANGED] LAPTOP {listing['listing_id']}")
                else:
                    session.execute(
                        text("""
                        INSERT INTO laptop_listings (
                            listing_id, title, description, price_eur, seller_location,
                            listing_url, image_url, date_posted,
                            brand, model, display_size, cpu_raw, cpu_freq_ghz,
                            ram_gb, storage_gb, storage_type, gpu_raw, seller_type, condition_state,
                            content_hash, is_active, source, laptop_reference_id, cpu_reference_id
                        ) VALUES (
                            :id, :title, :desc, :price, :location,
                            :url, :image_url, :date_posted,
                            :brand, :model, :display_size, :cpu_raw, :cpu_freq_ghz,
                            :ram_gb, :storage_gb, :storage_type, :gpu_raw, :seller_type, :condition_state,
                            :content_hash, true, 'ss.com', :laptop_reference_id, :cpu_reference_id
                        )
                        """),
                        {
                            **self._db_params(listing),
                            "laptop_reference_id": ref_id,
                            "cpu_reference_id": cpu_ref_id,
                        }
                    )

                    self.stats['new'] += 1
                    logger.info(f"[NEW] LAPTOP {listing['listing_id']}: {listing.get('brand', '')} {listing.get('model', '')} €{listing['price']}")

                image_url = listing.get('image_url')
                if image_url:
                    local_image_path = self.image_downloader.download_image(
                        image_url,
                        listing['listing_id']
                    )
                    if local_image_path:
                        logger.info(f"Image saved locally: {local_image_path}")
                        session.execute(
                            text("""
                            UPDATE laptop_listings
                            SET local_image_path = :path
                            WHERE listing_id = :id
                            """),
                            {"id": listing['listing_id'], "path": local_image_path}
                        )

                session.commit()
                return True

        except Exception as e:
            logger.error(f"[ERROR] Error saving laptop {listing['listing_id']}: {e}")
            self.stats['failed'] += 1
            return False

    def _save_version(self, session, listing_id: str):
        """Copy current row to listing_versions before updating."""
        try:
            session.execute(
                text("""
                INSERT INTO listing_versions (
                    listing_id, version_number, title, description,
                    price_eur, seller_location, content_hash
                )
                SELECT
                    listing_id,
                    COALESCE((SELECT MAX(version_number) FROM listing_versions
                              WHERE listing_id = :id), 0) + 1,
                    title, description, price_eur, seller_location, content_hash
                FROM laptop_listings
                WHERE listing_id = :id
                """),
                {"id": listing_id}
            )
        except Exception as e:
            logger.warning(f"Failed to save laptop version for {listing_id}: {e}")

    def _db_params(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Build DB parameter dict from parsed listing."""
        return {
            "id": listing['listing_id'],
            "title": listing['title'],
            "desc": listing['description'],
            "price": listing['price'],
            "location": listing['location'],
            "url": listing['url'],
            "image_url": listing.get('image_url'),
            "date_posted": listing.get('date_posted'),
            "brand": listing.get('brand'),
            "model": listing.get('model'),
            "display_size": listing.get('display_size'),
            "cpu_raw": listing.get('cpu_raw'),
            "cpu_freq_ghz": listing.get('cpu_freq_ghz'),
            "ram_gb": listing.get('ram_gb'),
            "storage_gb": listing.get('storage_gb'),
            "storage_type": listing.get('storage_type'),
            "gpu_raw": listing.get('gpu_raw'),
            "seller_type": listing.get('seller_type', 'private'),
            "condition_state": listing.get('condition_state'),
            "content_hash": listing.get('content_hash')
        }


class LaptopParser:
    """Parser for ss.com laptop listings."""

    def extract_listing_urls(self, html: str) -> List[tuple]:
        """Extract listing URLs from category page."""
        urls = []
        seen = set()
        soup = BeautifulSoup(html, 'html.parser')

        for link in soup.find_all('a', href=re.compile(r'/msg/')):
            href = link.get('href', '')
            if '/noutbooks/' in href:
                match = re.search(r'/([a-z]+)\.html$', href)
                if match:
                    listing_id = match.group(1)
                    if listing_id in seen:
                        continue
                    seen.add(listing_id)
                    full_url = href if href.startswith('http') else f"https://www.ss.com{href}"
                    urls.append((listing_id, full_url))

        return urls

    def has_next_page(self, html: str, current_page: int = 1) -> bool:
        """Check if there's a next page.

        SS.com marks pagination links with class ``navi`` and ``rel="next"/"prev"``.
        A next page exists when there is a ``rel="next"`` link whose ``href`` contains
        a page number greater than the current page.
        """
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', class_='navi'):
            rel = a.get('rel') or []
            if isinstance(rel, str):
                rel = rel.split()
            if 'next' not in rel:
                continue
            href = a.get('href') or ''
            m = re.search(r'page(\d+)\.html', href)
            if m and int(m.group(1)) > current_page:
                return True
        return False

    def parse_listing_page(self, html: str, listing_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse a single laptop listing page."""
        soup = BeautifulSoup(html, 'html.parser')

        title_elem = soup.find('title')
        title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""

        msg_div = soup.find('div', {'id': 'msg_div_msg'})
        description = ""
        if msg_div:
            description = msg_div.get_text(separator=' ', strip=True)

        price = self._extract_price(soup)
        location = self._extract_location(soup)
        image_url = self._extract_image_url(soup)
        date_posted = self._extract_date(soup)

        options = self._extract_options(soup)

        specs = {
            'listing_id': listing_id,
            'title': title,
            'description': description,
            'price': price,
            'location': location,
            'url': url,
            'image_url': image_url,
            'date_posted': date_posted,
            'brand': options.get('brand'),
            'model': options.get('model'),
            'display_size': options.get('display_size'),
            'cpu_raw': options.get('cpu_raw'),
            'cpu_freq_ghz': options.get('cpu_freq_ghz'),
            'ram_gb': self._parse_int(options.get('ram_gb')) or self._extract_ram_gb(description),
            'storage_gb': self._parse_int(options.get('storage_gb')) or self._extract_storage_gb(description),
            'storage_type': self._extract_storage_type(description),
            'gpu_raw': options.get('gpu_raw') or self._extract_gpu_raw(title + ' ' + description),
            'seller_type': self._extract_seller_type(soup),
            'condition_state': options.get('condition_state'),
        }

        # Normalize CPU string if it's just a model fragment (e.g. "I5-1135g7" -> "i5-1135g7")
        if specs['cpu_raw']:
            specs['cpu_raw'] = specs['cpu_raw'].strip()

        # If the options table gives only a generic family (e.g. "Intel Core i5"),
        # try to find a specific CPU model inside the free-text description.
        specs['cpu_raw'] = self._enrich_cpu_raw(specs['cpu_raw'], description)

        return specs

    @staticmethod
    def _extract_seller_type(soup: BeautifulSoup) -> str:
        """Classify the seller based on contacts/company info in the listing HTML."""
        # Perekups (resellers) are identified by the company name MS-27 — this takes
        # precedence over a seller logo because MS-27 listings are also branded.
        for td_name in soup.find_all('td', {'class': 'ads_contacts_name'}):
            if 'uzņēmums' in td_name.get_text(strip=True).lower():
                value_td = td_name.find_next_sibling('td', {'class': 'ads_contacts'})
                if value_td:
                    company = value_td.get_text(strip=True)
                    if company.lower() == 'ms-27':
                        return 'perekups'

        # Lombards listings carry a seller logo image
        logo_img = soup.find('img', {'id': 'usr_logo'})
        if logo_img:
            return 'lombards'

        return 'private'

    @staticmethod
    def _enrich_cpu_raw(cpu_raw: Optional[str], description: str) -> Optional[str]:
        """Replace a generic CPU family string with a specific model found in description."""
        if not cpu_raw and not description:
            return cpu_raw

        text = (description or "").lower()

        # If cpu_raw already contains a model number (e.g. "i5-10210u"), keep it.
        if cpu_raw and re.search(r'[-\s]\d{3,5}[a-z]*', cpu_raw.lower()):
            return cpu_raw

        old_lower = (cpu_raw or "").lower()

        # Infer brand/family from the existing generic cpu_raw so we don't replace
        # an AMD listing with an Intel CPU that happens to appear in the description.
        old_brand = None
        if any(k in old_lower for k in ['intel', 'core', 'i3', 'i5', 'i7', 'i9', 'pentium', 'celeron', 'xeon']):
            old_brand = 'intel'
        elif any(k in old_lower for k in ['amd', 'ryzen', 'athlon']):
            old_brand = 'amd'

        old_family = None
        family_match = re.search(r'\b(i[3579]|ryzen\s+[3579]|athlon|pentium|celeron)\b', old_lower)
        if family_match:
            old_family = family_match.group(1).replace(' ', '')

        candidates = []

        # Intel patterns (Core i3/i5/i7/i9, Pentium, Celeron, Xeon)
        intel_patterns = [
            (r'intel\s+core\s+(i[3579])\s*[-\s]\s*(\d{3,5}[a-z]*)', 'intel'),
            (r'core\s+(i[3579])\s*[-\s]\s*(\d{3,5}[a-z]*)', 'intel'),
            (r'\b(i[3579])\s*[-\s]\s*(\d{3,5}[a-z]*)', 'intel'),
            (r'intel\s+(pentium|celeron)\s+([a-z]?\d{3,4}[a-z]*)', 'intel'),
            (r'\b(xeon)\s+([a-z]?\d{3,5}[a-z]*)', 'intel'),
        ]
        for pattern, brand in intel_patterns:
            for match in re.finditer(pattern, text):
                family = match.group(1)
                model = match.group(2)
                name = f"Intel Core {family}-{model}" if family.startswith('i') else f"Intel {family.capitalize()} {model}"
                candidates.append((name, brand, family, match.start()))

        # AMD patterns (Ryzen 3/5/7/9, Athlon, FX)
        amd_patterns = [
            (r'amd\s+ryzen\s+([3579])\s*[-\s]\s*(\d{4,5}[a-z]*)', 'amd'),
            (r'ryzen\s+([3579])\s*[-\s]\s*(\d{4,5}[a-z]*)', 'amd'),
            (r'\b(athlon)\s+(\d{4}[a-z]*)', 'amd'),
            (r'\b(fx[-\s]?\d{4})', 'amd'),
        ]
        for pattern, brand in amd_patterns:
            for match in re.finditer(pattern, text):
                if 'fx' in pattern:
                    family = match.group(1).replace('-', '').upper()
                    name = f"AMD FX {family}"
                    candidates.append((name, brand, family, match.start()))
                else:
                    family = match.group(1)
                    model = match.group(2)
                    candidates.append((f"AMD Ryzen {family} {model}", brand, family, match.start()))

        if not candidates:
            return cpu_raw

        # Enforce brand/family consistency with the generic cpu_raw when known.
        def compatible(c):
            c_brand, c_family = c[1], c[2].replace(' ', '')
            if old_brand and c_brand != old_brand:
                return False
            if old_family and c_family != old_family:
                return False
            return True

        candidates = [c for c in candidates if compatible(c)]
        if not candidates:
            return cpu_raw

        # Prefer the earliest mention in the description, then the longest/specific string.
        candidates.sort(key=lambda x: (x[3], -len(x[0])))
        return candidates[0][0]

    def _extract_options(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract key/value pairs from the SS.com options table."""
        options = {}

        for tr in soup.find_all('tr'):
            label_td = tr.find('td', {'class': 'ads_opt_name'})
            value_td = tr.find('td', {'class': 'ads_opt'})
            if not label_td or not value_td:
                continue

            label = label_td.get_text(strip=True).lower()
            value = value_td.get_text(strip=True)

            if 'marka' in label:
                options['brand'] = value
            elif 'modelis' in label and 'modelis' not in options:
                options['model'] = value
            elif 'displejs' in label:
                options['display_size'] = value
            elif label.startswith('procesors') or 'procesor' in label:
                # Avoid overwriting if multiple CPU rows exist; first wins
                if 'cpu_raw' not in options:
                    options['cpu_raw'] = value
            elif 'videokarte' in label or 'video' in label or 'grafika' in label or 'graphics' in label:
                if 'gpu_raw' not in options:
                    options['gpu_raw'] = value
            elif 'frekvence' in label:
                options['cpu_freq_ghz'] = value
            elif 'hdd apjoms' in label or 'cietais' in label:
                options['storage_gb'] = value
            elif 'operatīvā' in label or 'atmiņa' in label:
                options['ram_gb'] = value
            elif 'stavoklis' in label or 'состояние' in label or 'статус' in label:
                options['condition_state'] = value

        return options

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
        """Extract location, skipping phone UI."""
        for label_td in soup.find_all('td', {'class': 'ads_contacts_name'}):
            label_text = label_td.get_text(strip=True).lower()
            if 'vieta' in label_text or 'место' in label_text:
                value_td = label_td.find_next_sibling('td', {'class': 'ads_contacts'})
                if value_td:
                    full_text = value_td.get_text(strip=True)
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    for line in lines:
                        if not re.search(r'\(\+\d+\)|tālruni|parādīt', line, re.IGNORECASE):
                            return line
                    break

        address = soup.find('td', {'class': 'td_address'})
        if address:
            return address.get_text(strip=True)

        return ""

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main listing image URL."""
        main_img = soup.find('img', {'id': 'msg_img_img'})
        if main_img and main_img.get('src'):
            image_url = main_img['src']
        else:
            thumb_link = soup.select_one('#tr_foto a[href*=".800.jpg"]')
            image_url = thumb_link['href'] if thumb_link and thumb_link.get('href') else None

        if image_url and image_url.startswith('/'):
            image_url = f"https://i.ss.com{image_url}"

        return image_url

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract listing date from footer."""
        for td in soup.select('td.msg_footer'):
            text = td.get_text(strip=True)
            match = re.search(r'Datums:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', text)
            if match:
                day, month, year, hour, minute = match.groups()
                try:
                    return datetime(int(year), int(month), int(day), int(hour), int(minute))
                except ValueError:
                    pass
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
            if match:
                year, month, day = match.groups()
                try:
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    pass
        return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        """Safely parse an integer from a string."""
        if value is None:
            return None
        cleaned = re.sub(r'[^0-9]', '', str(value))
        try:
            return int(cleaned) if cleaned else None
        except ValueError:
            return None

    @staticmethod
    def _extract_ram_gb(description: str) -> Optional[int]:
        """Extract RAM capacity in GB from description."""
        if not description:
            return None
        text_lower = description.lower()
        # Russian and Latvian hints
        patterns = [
            r'оперативная\s*память\s*(\d+)\s*gb',
            r'оперативная\s*память\s*(\d+)\s*гб',
            r'ram\s*(\d+)\s*gb',
            r'ddr[3456].*?(\d+)\s*gb',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_storage_gb(description: str) -> Optional[int]:
        """Extract storage capacity in GB from description."""
        if not description:
            return None
        text_lower = description.lower()
        patterns = [
            r'ssd\s*жесткий\s*диск\s*(\d+)\s*gb',
            r'ssd\s*(\d+)\s*gb',
            r'жесткий\s*диск\s*(\d+)\s*gb',
            r'hdd\s*(\d+)\s*gb',
            r'hdd\s*(\d+)\s*tb',
            r'ssd\s*(\d+)\s*tb',
            r'диск\s*(\d+)\s*gb',
        ]
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = int(match.group(1))
                if 'tb' in pattern:
                    val *= 1000
                return val
        return None

    @staticmethod
    def _extract_storage_type(description: str) -> Optional[str]:
        """Guess storage type from description."""
        if not description:
            return None
        text_lower = description.lower()
        if 'ssd' in text_lower:
            return 'SSD'
        if 'hdd' in text_lower or 'жесткий диск' in text_lower:
            return 'HDD'
        if 'emmc' in text_lower:
            return 'eMMC'
        return None

    @staticmethod
    def _extract_gpu_raw(text: str) -> Optional[str]:
        """Extract GPU mention from title + description."""
        if not text:
            return None
        text_lower = text.lower()

        # 1) Dedicated GPUs (prefer these over integrated graphics)
        dgpu_patterns = [
            # NVIDIA — GeForce, GT and Quadro
            r'nvidia\s+geforce\s+(rtx\s*\d{3,4}(?:\s*(?:ti|super))?)',
            r'geforce\s+(rtx\s*\d{3,4}(?:\s*(?:ti|super))?)',
            r'\b(rtx\s*\d{3,4}(?:\s*(?:ti|super))?)\b',
            r'nvidia\s+geforce\s+(gtx\s*\d{3,4}(?:\s*(?:ti|super))?)',
            r'geforce\s+(gtx\s*\d{3,4}(?:\s*(?:ti|super))?)',
            r'\b(gtx\s*\d{3,4}(?:\s*(?:ti|super))?)\b',
            r'geforce\s+(mx\s*\d{3,4})',
            r'\b(mx\s*\d{3,4})\b',
            r'nvidia\s+geforce\s+(gt\s*\d{3,4})',
            r'geforce\s+(gt\s*\d{3,4})',
            r'\b(gt\s*\d{3,4})\b',
            r'nvidia\s+(quadro\s+[a-z]?\d{3,4}\w*)',
            r'\b(quadro\s+[a-z]?\d{3,4}\w*)',
            # AMD — RX, RX Vega, Vega, Radeon Pro
            r'amd\s+radeon\s+(rx\s*\d{3,4}(?:\s*(?:m|xt|xtx))?)',
            r'amd\s+radeon\s+(rx\s+vega\s*\d+)',
            r'amd\s+radeon\s+(\d{3,4}[a-z]?)',
            r'radeon\s+(rx\s*\d{3,4}(?:\s*(?:m|xt|xtx))?)',
            r'radeon\s+(rx\s+vega\s*\d+)',
            r'radeon\s+(\d{3,4}[a-z]?)',
            r'amd\s+radeon\s+(vega\s*\d+)',
            r'radeon\s+(vega\s*\d+)',
            r'amd\s+radeon\s+(pro\s*\d{3,4}[a-z]?)',
            r'radeon\s+(pro\s*\d{3,4}[a-z]?)',
        ]
        for pattern in dgpu_patterns:
            match = re.search(pattern, text_lower)
            if match:
                raw = match.group(1).strip()
                raw = re.sub(r'\s+', ' ', raw)
                # Insert a space between kind and number for strings like "gtx1650ti"
                raw = re.sub(r'\b(rtx|gtx|mx|gt|rx|vega|pro)(\d)', r'\1 \2', raw, flags=re.IGNORECASE)
                parts = raw.split()
                if not parts:
                    continue
                kind = parts[0].upper()
                if kind in ('RTX', 'GTX', 'MX', 'GT'):
                    number = parts[1] if len(parts) > 1 else ''
                    suffix = ' '.join(p.upper() for p in parts[2:]) if len(parts) > 2 else ''
                    name = f"NVIDIA GeForce {kind} {number}".strip()
                    if suffix:
                        name = f"{name} {suffix}".strip()
                    return name
                elif kind in ('RX', 'VEGA'):
                    # Uppercase RX, keep Vega title-cased
                    return re.sub(r'\bRx\b', 'RX', f"AMD Radeon {raw.title()}")
                elif kind == 'PRO':
                    number = parts[1] if len(parts) > 1 else ''
                    return f"AMD Radeon Pro {number.upper()}"
                elif 'QUADRO' in kind or kind.startswith('QUADRO'):
                    return f"NVIDIA {raw.title()}"
                elif re.match(r'\d', kind[0]):
                    # Bare AMD model number like "Radeon 740M"
                    return f"AMD Radeon {raw.upper()}"
                else:
                    return f"NVIDIA GeForce {raw.title()}"

        # 2) Intel integrated graphics
        igpu_patterns = [
            r'intel\s+(iris\s+plus\s+graphics)\s*(\d{3,4})?',
            r'intel\s+(iris\s+xe\s+graphics)\s*(\d{3,4})?',
            r'intel\s+(uhd\s+graphics)\s*(\d{3,4})?',
            r'intel\s+(hd\s+graphics)\s*(\d{3,4})?',
            r'intel\s+(iris\s+graphics)\s*(\d{3,4})?',
            r'\b(iris\s+plus\s+graphics)\s*(\d{3,4})?',
            r'\b(iris\s+xe\s+graphics)\s*(\d{3,4})?',
            r'\b(uhd\s+graphics)\s*(\d{3,4})?',
            r'\b(hd\s+graphics)\s*(\d{3,4})?',
        ]
        for pattern in igpu_patterns:
            match = re.search(pattern, text_lower)
            if match:
                name = match.group(1).strip().title()
                digits = match.group(2)
                if digits:
                    return f"Intel {name} {digits}"
                return f"Intel {name}"

        # 3) Generic "videokarte:" / "graphics card:" lines without a known model
        # are skipped — returning free-text here tends to grab the rest of the description.
        return None
