"""CPU listing HTML parser for ss.com."""
import re
from datetime import datetime
from typing import Optional, List
from bs4 import BeautifulSoup

from src.models.schemas import Listing, CPUMatchResult, CPUReference
from src.utils.text import normalize_text, compute_content_hash
from src.utils.logger import get_logger

logger = get_logger("cpu_parser")


class CPUListingParser:
    """Parse ss.com CPU listing HTML into structured data."""
    
    # CSS selectors (similar to GPU parser)
    SELECTORS = {
        'title': 'h2',
        'price': '.ads_price',
        'description': '#msg_div_msg',
        'image': 'img.pic_thumbnail',
        'date': 'td.msg_footer',
        'location': 'td.ads_contacts',
        'brand_row': 'td.ads_opt_name:-soup-contains("Marka")',
        'brand_value': 'td.ads_opt',
        'options_table': 'table.options_list',
    }
    
    # Price pattern
    PRICE_PATTERN = re.compile(r'[\d\s.,]+')
    
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
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)
        
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
        Extract CPU brand/model from the options table.
        Looks for "Marka:" (Brand) row.
        """
        for label_td in self.soup.find_all('td', class_='ads_opt_name'):
            label_text = label_td.get_text(strip=True)
            if 'marka' in label_text.lower():
                value_td = label_td.find_next_sibling('td', class_='ads_opt')
                if value_td:
                    value = value_td.get_text(strip=True)
                    value = re.sub(r'^Cits\s*', '', value, flags=re.IGNORECASE).strip()
                    return value if value else None
        return None
    
    def _extract_frequency(self) -> Optional[float]:
        """
        Extract CPU base frequency from the options table.
        Looks for "Frekvence, GHz:" (Frequency) row.
        """
        for label_td in self.soup.find_all('td', class_='ads_opt_name'):
            label_text = label_td.get_text(strip=True)
            if 'frekvence' in label_text.lower():
                value_td = label_td.find_next_sibling('td', class_='ads_opt')
                if value_td:
                    value_text = value_td.get_text(strip=True)
                    # Parse GHz value
                    match = re.search(r'(\d+(?:\.\d+)?)', value_text)
                    if match:
                        try:
                            return float(match.group(1))
                        except ValueError:
                            pass
        return None
    
    def _extract_price(self) -> Optional[float]:
        """Extract price from price element."""
        price_elem = self.soup.select_one(self.SELECTORS['price'])
        if not price_elem:
            return None
        
        price_text = price_elem.get_text(strip=True)
        price_clean = price_text.replace('€', '').replace(' ', '').replace(',', '.')
        
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
        
        text_parts = []
        
        for child in desc_elem.children:
            if child.name == 'div' and 'float' in child.get('style', ''):
                continue
            if child.name == 'table':
                if 'options_list' in child.get('class', []) or child.find('img'):
                    continue
            
            text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
            if text:
                text_parts.append(text)
        
        if not text_parts:
            full_text = desc_elem.get_text(separator='\n', strip=True)
            text_parts = [full_text]
        
        return '\n'.join(text_parts) if text_parts else None
    
    def _extract_date(self) -> Optional[datetime]:
        """Extract date from footer."""
        for td in self.soup.select(self.SELECTORS['date']):
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
    
    def _extract_location(self) -> Optional[str]:
        """Extract seller location from contacts."""
        for td in self.soup.select('td.ads_contacts_name'):
            label = td.get_text(strip=True)
            if 'Vieta' in label:
                value_td = td.find_next_sibling('td', class_='ads_contacts')
                if value_td:
                    return value_td.get_text(strip=True)
        return None
    
    def _extract_image(self) -> Optional[str]:
        """Extract main image URL."""
        img = self.soup.select_one(self.SELECTORS['image'])
        if img:
            src = img.get('src') or img.get('data-src')
            if src:
                if src.startswith('//'):
                    return f"https:{src}"
                elif src.startswith('/'):
                    return f"https://www.ss.com{src}"
                return src
        return None
    
    def parse(self) -> Optional[Listing]:
        """
        Parse HTML into Listing object.
        
        Returns:
            Listing object or None if critical fields missing
        """
        brand_model = self._extract_brand_model()
        description = self._extract_description()
        
        if brand_model:
            title = brand_model
        elif description:
            first_line = description.split('\n')[0][:200]
            title = first_line
        else:
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
        image_url = self._extract_image()
        
        # Extract base frequency for CPU matching
        base_freq = self._extract_frequency()
        base_freq_mhz = int(base_freq * 1000) if base_freq else None
        
        content_hash = compute_content_hash(title, price or 0, location or "")
        
        return Listing(
            listing_id=self.listing_id,
            title=title,
            description=description,
            price_eur=price or 0,
            seller_location=location,
            listing_url=self.url,
            image_url=image_url,
            date_posted=date_posted,
            category='cpu',
            base_freq_mhz=base_freq_mhz,
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
        
        for link_elem in self.soup.select('tr a[href*="/msg/"]'):
            if link_elem:
                href = link_elem.get('href')
                if href:
                    if href.startswith('/'):
                        href = f"https://www.ss.com{href}"
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
        next_link = self.soup.find('a', text=re.compile(r'Nākošie'))
        if next_link:
            href = next_link.get('href')
            if href:
                if href.startswith('/'):
                    return f"https://www.ss.com{href}"
                return href
        return None
