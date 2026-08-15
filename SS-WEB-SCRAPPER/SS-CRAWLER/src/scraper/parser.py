"""HTML parser for ss.com listings."""
import re
from datetime import datetime
from typing import Optional, List, Dict
from bs4 import BeautifulSoup

from src.models.schemas import Listing, MatchResult, GPUReference
from src.utils.text import normalize_text, compute_content_hash
from src.utils.logger import get_logger

logger = get_logger("parser")


class ListingParser:
    """Parse ss.com listing HTML into structured data."""

    # CSS selectors (update if site changes)
    SELECTORS = {
        # Note: h2 is category path, not product title
        'title': 'h2',
        'price': '.ads_price',
        'description': '#msg_div_msg',
        'image': 'img.pic_thumbnail',
        'date': 'td.msg_footer',
        'location': 'td.ads_contacts',
        'brand_row': 'td.ads_opt_name:-soup-contains("Marka")',  # "Marka:" = Brand
        'brand_value': 'td.ads_opt',  # The value next to "Marka:"
        'options_table': 'table.options_list',  # Table with Marka, VRAM, etc.
    }

    # Skip patterns applied to title + description + seller name
    SKIP_PATTERNS = [
        "multisistēma rīga",
        "multisistema riga",
        "garantija - 2 gadi",
        "garantija 2 gadi",
        "diagnostiku un remontu",
    ]

    # Price pattern
    PRICE_PATTERN = re.compile(r'[\d\s.,]+')

    # Date patterns for ss.com
    DATE_PATTERNS = [
        r'Datums:\s*(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2})',
    ]

    def __init__(self, html: str, url: str):
        """
        Initialize parser with HTML content.

        Args:
            html: Raw HTML string
            url: Listing URL (for extracting ID)
        """
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'html.parser')

        # Extract listing ID from URL
        self.listing_id = self._extract_listing_id(url)

    def _extract_listing_id(self, url: str) -> str:
        """Extract listing ID from URL."""
        # URL format: .../sell/ID.html
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)

        # Fallback: last part of path without .html
        parts = url.rstrip('/').split('/')
        last = parts[-1] if parts else 'unknown'
        return last.replace('.html', '')

    def _extract_text(self, selector: str) -> Optional[str]:
        """Extract and clean text from element."""
        elem = self.soup.select_one(selector)
        if elem:
            return elem.get_text(strip=True) or None
        return None

    def _extract_brand_model(self) -> Optional[str]:
        """
        Extract GPU brand/model from the options table.
        Looks for "Marka:" (Brand) row.
        """
        # Look for td with class 'ads_opt_name' that contains 'Marka:'
        for label_td in self.soup.find_all('td', class_='ads_opt_name'):
            label_text = label_td.get_text(strip=True)
            if 'marka' in label_text.lower():
                # Find the next sibling td with class 'ads_opt' (the value)
                value_td = label_td.find_next_sibling('td', class_='ads_opt')
                if value_td:
                    value = value_td.get_text(strip=True)
                    # Clean up "Cits" (Other) prefix
                    value = re.sub(r'^Cits\s*', '', value, flags=re.IGNORECASE).strip()
                    return value if value else None

        return None

    def _extract_vram_mb(self) -> Optional[int]:
        """
        Extract VRAM size from 'Atmiņas apjoms, Mb:' field.
        Returns value in MB.
        Also applies common typo corrections (e.g., 1200 -> 12000).
        """
        for label_td in self.soup.find_all('td', class_='ads_opt_name'):
            label_text = label_td.get_text(strip=True)
            # Look for "Atmiņas apjoms" (Memory amount) or contains "Mb"
            if 'atmiņas' in label_text.lower() or 'mb' in label_text.lower():
                value_td = label_td.find_next_sibling('td', class_='ads_opt')
                if value_td:
                    value_text = value_td.get_text(strip=True)
                    # Extract number
                    match = re.search(r'(\d+)', value_text.replace(' ', ''))
                    if match:
                        vram = int(match.group(1))
                        return self._correct_vram_typo(vram, value_text)
        return None

    def _correct_vram_typo(self, vram_value: int, value_text: str = "") -> int:
        """
        Correct common VRAM entry typos and unit mismatches.

        Common mistakes:
        - 1200 MB -> meant 12000 MB (12 GB)
        - 2400 MB -> meant 24000 MB (24 GB)
        - 800 MB -> meant 8000 MB (8 GB)
        - 1600 MB -> meant 16000 MB (16 GB)
        - 600 MB -> meant 6000 MB (6 GB)
        - 400 MB -> meant 4000 MB (4 GB)
        - 2 MB -> meant 2 GB (2048 MB) [value entered as GB not MB]

        Logic:
        1. If value is labeled as GB (has 'gb' or 'g'), convert to MB
        2. If value is suspiciously low (< 100 MB), assume it's in GB
        3. If value * 10 gives standard VRAM size, apply correction
        """
        # Check if value text explicitly indicates GB
        value_lower = value_text.lower()
        has_gb_suffix = 'gb' in value_lower or 'гб' in value_lower

        # Explicit GB notation - convert to MB
        if has_gb_suffix and vram_value <= 64:  # Reasonable GPU VRAM in GB
            corrected = vram_value * 1024
            logger.debug(f"VRAM unit conversion: {vram_value} GB -> {corrected} MB")
            return corrected

        # If value is already >= 2048 MB, it's likely correct
        if vram_value >= 2048:
            return vram_value

        # Very small values (1-64) likely mean GB, not MB
        # Example: "2" in field labeled "Mb:" actually means 2 GB (2048 MB)
        if 1 <= vram_value <= 64:
            corrected = vram_value * 1024
            logger.debug(f"VRAM unit inferred: {vram_value} likely GB -> {corrected} MB")
            return corrected

        # Standard VRAM sizes in MB
        standard_sizes = {4096, 6144, 8192, 12288, 16384, 24576}

        # Check if value * 10 is a standard size (typo: missing zero)
        corrected = vram_value * 10
        if corrected in standard_sizes:
            logger.debug(f"VRAM typo corrected: {vram_value} MB -> {corrected} MB")
            return corrected

        # Also check for values like 600, 1200, 2400 that might need * 10
        # but don't exactly match (due to rounding in some displays)
        if 300 <= vram_value < 500:
            return 4096  # 400 -> 4096
        if 1100 <= vram_value < 1300:  # 1200 area
            return 12288  # Likely meant 12 GB
        if 2300 <= vram_value < 2500:  # 2400 area
            return 24576  # Likely meant 24 GB
        if 700 <= vram_value < 900:  # 800 area
            return 8192  # Likely meant 8 GB
        if 1500 <= vram_value < 1700:  # 1600 area
            return 16384  # Likely meant 16 GB
        if 550 <= vram_value < 650:  # 600 area
            return 6144  # Likely meant 6 GB

        return vram_value

    def _extract_price(self) -> Optional[float]:
        """Extract price from price element."""
        price_elem = self.soup.select_one(self.SELECTORS['price'])
        if not price_elem:
            return None

        price_text = price_elem.get_text(strip=True)

        # Remove euro symbol and whitespace
        price_clean = price_text.replace('€', '').replace(' ', '').replace(',', '.')

        # Extract number
        match = re.search(r'[\d.]+', price_clean)
        if match:
            try:
                return float(match.group())
            except ValueError:
                logger.warning(f"Could not parse price: {price_text}")

        return None

    def _extract_description(self) -> Optional[str]:
        """Extract description, cleaning up the HTML."""
        desc_elem = self.soup.select_one(self.SELECTORS['description'])
        if not desc_elem:
            return None

        # Find the main text div (msg_div_msg contains both description and options table)
        # The description is usually in a div directly, before any tables
        text_parts = []

        for child in desc_elem.children:
            if child.name == 'div' and 'float' in child.get('style', ''):
                # Skip floating divs (usually empty content_sys_div_msg)
                continue
            if child.name == 'table':
                # Skip option tables and image tables
                if 'options_list' in child.get('class', []) or child.find('img'):
                    continue

            # Extract text from this element
            text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
            if text:
                text_parts.append(text)

        # Also try to get the first text node before any tables
        if not text_parts:
            # Fallback: get all text, exclude option tables
            full_text = desc_elem.get_text(separator='\n', strip=True)
            text_parts = [full_text]

        return '\n'.join(text_parts) if text_parts else None

    def _extract_date(self) -> Optional[datetime]:
        """Extract date from footer."""
        for td in self.soup.select(self.SELECTORS['date']):
            text = td.get_text(strip=True)

            # Look for "Datums: DD.MM.YYYY HH:MM"
            match = re.search(r'Datums:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', text)
            if match:
                day, month, year, hour, minute = match.groups()
                try:
                    return datetime(int(year), int(month), int(day), int(hour), int(minute))
                except ValueError:
                    pass

            # Fallback: ISO date
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
            if match:
                year, month, day = match.groups()
                try:
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    pass

        return None

    def _extract_seller_name(self) -> Optional[str]:
        """Extract seller name / contact person from the contacts table."""
        name_labels = ['vārds', 'vards', 'kontaktpersona', 'kontakti', 'name', 'contacts']
        for td in self.soup.select('td.ads_contacts_name'):
            label = td.get_text(strip=True).lower().rstrip(':')
            if any(lbl in label for lbl in name_labels):
                value_td = td.find_next_sibling('td', class_='ads_contacts')
                if value_td:
                    return value_td.get_text(strip=True)
        return None

    def _extract_location(self) -> Optional[str]:
        """Extract seller location from contacts."""
        # Look for "Vieta:" in contacts
        for td in self.soup.select('td.ads_contacts_name'):
            label = td.get_text(strip=True)
            if 'Vieta' in label:
                value_td = td.find_next_sibling('td', class_='ads_contacts')
                if value_td:
                    location = value_td.get_text(strip=True)
                    # Skip "Interneta veikals" (online store) listings
                    if location and 'interneta' in location.lower():
                        logger.info(f"Skipping online store listing: {location}")
                        return None
                    # Skip if location looks like a brand name (not a place)
                    brand_names = ['gigabyte', 'asus', 'msi', 'evga', 'sapphire', 'xfx', 'palit', 'zotac',
                                   'nvidia', 'amd', 'intel', 'kingston', 'crucial', 'samsung', 'wd',
                                   'seagate', 'toshiba', 'corsair', 'cooler master', 'be quiet',
                                   'seasonic', 'thermaltake', 'phanteks', 'nzxt', 'fractal']
                    if location and any(brand in location.lower() for brand in brand_names):
                        logger.info(f"Skipping brand name as location: {location}")
                        return None
                    return location
        return None

    def _extract_image(self) -> Optional[str]:
        """Extract main image URL and convert to full size.

        ss.com listings show real gallery images under the 'Foto:' section
        (URLs like https://i.ss.com/gallery/.../photo-optics-...jpg.800.jpg).
        The old img.pic_thumbnail src now often returns a 1x1 GIF placeholder,
        so we prefer gallery URLs when available.
        """
        # 1) Prefer real gallery images from the 'Foto:' section
        gallery_links = self.soup.select('a[href*="i.ss.com/gallery/"]')
        if gallery_links:
            href = gallery_links[0].get('href')
            if href:
                return self._normalize_image_url(href)

        # 2) Also try images whose src already points to the gallery CDN
        gallery_imgs = self.soup.select('img[src*="i.ss.com/gallery/"]')
        if gallery_imgs:
            src = gallery_imgs[0].get('src') or gallery_imgs[0].get('data-src')
            if src:
                return self._normalize_image_url(src)

        # 3) Fall back to the legacy thumbnail selector
        img = self.soup.select_one(self.SELECTORS['image'])
        if img:
            src = img.get('src') or img.get('data-src')
            if src:
                return self._normalize_image_url(src)
        return None

    def _normalize_image_url(self, src: str) -> str:
        """Make image URL absolute and prefer the largest available size."""
        # Make absolute URL
        if src.startswith('//'):
            src = f"https:{src}"
        elif src.startswith('/'):
            src = f"https://www.ss.com{src}"

        # Convert thumbnail URL to the largest available size.
        # ss.com thumbnails are .t.jpg; full/largest version is .800.jpg.
        # Older patterns: .thumb. and .th. -> strip and append .800.
        if src.endswith('.t.jpg'):
            src = f"{src[:-6]}.800.jpg"
        elif '.thumb.' in src:
            src = src.replace('.thumb.', '.')[:-4] + '.800.jpg' if src.endswith('.jpg') else src.replace('.thumb.', '.') + '.800.jpg'
        elif '.th.' in src:
            src = src.replace('.th.', '.')[:-4] + '.800.jpg' if src.endswith('.jpg') else src.replace('.th.', '.') + '.800.jpg'

        return src

    def _extract_seller_note(self) -> Optional[str]:
        """
        Extract the seller's short note from the title area.
        On ss.com, h2 contains: "Category > Subcategory / Pārdod" or similar
        The last part (after last "/") might contain seller's note.
        """
        title_elem = self.soup.select_one('h2')
        if title_elem:
            text = title_elem.get_text(strip=True)
            # Look for "Pārdod" (Selling), "Pērk" (Buying), etc.
            parts = text.split('/')
            if len(parts) > 1:
                last_part = parts[-1].strip()
                # Filter out common non-descriptive text
                if last_part and last_part not in ['Pārdod', 'Pērk', 'Maina']:
                    return last_part
        return None

    def parse(self) -> Optional[Listing]:
        """
        Parse HTML into Listing object.

        Returns:
            Listing object or None if critical fields missing
        """
        # Try to get brand/model from options table first
        brand_model = self._extract_brand_model()

        # Get description
        description = self._extract_description()

        # Build effective title for matching:
        # Priority: Brand/Model > Description first line > h2 fallback
        if brand_model:
            title = brand_model
        elif description:
            # Take first line of description as title
            first_line = description.split('\n')[0][:200]
            title = first_line
        else:
            # Fallback to h2 (category path)
            title_elem = self.soup.select_one('h2')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        if not title:
            logger.error(f"No title found for {self.url}")
            return None

        price = self._extract_price()
        if price is None:
            logger.warning(f"No price found for {self.url}")

        date_posted = self._extract_date()
        location = self._extract_location()

        # Skip buying listings (people looking to buy, not sell)
        title_lower = title.lower()
        if any(word in title_lower for word in ['pērku', 'perku', 'pērk', 'perk']):
            logger.info(f"Skipping buying listing: {title}")
            return None

        # Skip online store listings by title
        if any(word in title_lower for word in ['veikals', 'interneta']):
            logger.info(f"Skipping store listing by title: {title}")
            return None

        # Skip buying/store listings in description
        if description:
            desc_lower = description.lower()
            if any(word in desc_lower for word in ['pērku', 'perku', 'pērk', 'perk']):
                logger.info(f"Skipping buying listing by description: {title}")
                return None
            if 'veikals' in desc_lower or 'interneta veikals' in desc_lower:
                logger.info(f"Skipping store listing by description: {title}")
                return None
            # Skip dealer/shop listings by description patterns
            skip_text = (title + " " + description).lower()
            if any(pattern in skip_text for pattern in self.SKIP_PATTERNS):
                logger.info(f"Skipping listing by skip pattern: {title}")
                return None

        # Skip dealer/shop listings by seller name
        seller_name = self._extract_seller_name() or ""
        full_text_lower = f"{title} {description or ''} {seller_name}".lower()
        if any(pattern in full_text_lower for pattern in self.SKIP_PATTERNS):
            logger.info(f"Skipping listing by seller/pattern: {title}")
            return None

        # Skip online store listings
        if location is None:
            logger.info(f"Skipping online store listing: {self.url}")
            return None

        image_url = self._extract_image()
        image_url = self._extract_image()
        vram_mb = self._extract_vram_mb()

        # Compute content hash for duplicate detection
        content_hash = compute_content_hash(title, price or 0, location or "")

        return Listing(
            listing_id=self.listing_id,
            title=title,
            description=description,
            price_eur=price or 0,
            vram_mb=vram_mb,
            seller_location=location,
            listing_url=self.url,
            image_url=image_url,
            date_posted=date_posted,
            content_hash=content_hash
        )

    def get_category_links(self) -> List[str]:
        """
        Extract all listing links from category page.

        Returns:
            List of absolute URLs
        """
        links = []
        seen = set()

        # ss.com uses table rows with message links (look for /msg/ URLs in rows)
        for link_elem in self.soup.select('tr a[href*="/msg/"]'):
            if link_elem:
                href = link_elem.get('href')
                if href:
                    # Make absolute URL
                    if href.startswith('/'):
                        href = f"https://www.ss.com{href}"
                    # Deduplicate
                    if href not in seen:
                        seen.add(href)
                        links.append(href)

        logger.info(f"Found {len(links)} listings on page")
        return links

    def has_next_page(self) -> Optional[str]:
        """
        Check for pagination and return next page URL if exists.

        Returns:
            Next page URL or None
        """
        # Look for "Nākošie" (Next) link
        next_link = self.soup.find('a', text=re.compile(r'Nākošie'))
        if next_link:
            href = next_link.get('href')
            if href:
                if href.startswith('/'):
                    return f"https://www.ss.com{href}"
                return href
        return None
