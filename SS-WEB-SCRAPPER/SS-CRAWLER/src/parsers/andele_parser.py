"""Parser for Andele Mandele HTML structure."""
import re
import logging
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("andele_parser")


class AndeleListingData:
    """Data class for parsed Andele listing."""
    
    def __init__(self):
        self.listing_id: Optional[str] = None
        self.title: str = ""
        self.description: Optional[str] = None
        self.price_eur: Optional[float] = None
        self.seller_location: Optional[str] = None
        self.listing_url: str = ""
        self.image_urls: List[str] = []
        self.date_posted: Optional[datetime] = None
        self.category: str = "general"
        self.raw_html: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'listing_id': self.listing_id,
            'title': self.title,
            'description': self.description,
            'price_eur': self.price_eur,
            'seller_location': self.seller_location,
            'listing_url': self.listing_url,
            'image_urls': self.image_urls,
            'date_posted': self.date_posted,
            'category': self.category,
        }


class AndeleParser:
    """Parser for Andele Mandele marketplace HTML."""
    
    BASE_URL = "https://www.andelemandele.lv"
    
    # Category URL mappings (attribute IDs)
    CATEGORY_URLS = {
        'gpu': '/perles/tehnika/datori/#order:actual/attributes:409',
        'cpu': '/perles/tehnika/datori/#order:actual/attributes:405',
        'ssd': '/perles/tehnika/datori/#order:actual/attributes:404',
        'ram': '/perles/tehnika/datori/#order:actual/attributes:406',
        'psu': '/perles/tehnika/datori/#order:actual/attributes:415',
        'computer': '/perles/tehnika/datori/#order:actual/attributes:413',
        'monitor': '/perles/tehnika/datori/#order:actual/attributes:578',
        'motherboard': '/perles/tehnika/datori/#order:actual/attributes:403',
    }
    
    def __init__(self):
        self.logger = logging.getLogger("andele_parser")
        
    def get_category_url(self, category: str) -> str:
        """Get URL for specific category."""
        path = self.CATEGORY_URLS.get(category, '/perles/tehnika/datori/')
        return f"{self.BASE_URL}{path}"
        
    def parse_listing_page(self, html: str, url: str) -> AndeleListingData:
        """Parse a single listing page.
        
        Args:
            html: HTML content of the listing page
            url: URL of the listing
            
        Returns:
            AndeleListingData with extracted information
        """
        soup = BeautifulSoup(html, 'html.parser')
        data = AndeleListingData()
        data.listing_url = url
        data.listing_id = self._extract_listing_id(url)
        data.raw_html = html
        
        try:
            # Extract title
            data.title = self._extract_title(soup)
            
            # Extract price
            data.price_eur = self._extract_price(soup)
            
            # Extract description
            data.description = self._extract_description(soup)
            
            # Extract images
            data.image_urls = self._extract_images(soup)
            
            # Extract location
            data.seller_location = self._extract_location(soup)
            
            # Extract date
            data.date_posted = self._extract_date(soup)
            
            self.logger.debug(f"Parsed listing {data.listing_id}: {data.title[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error parsing listing page {url}: {e}")
            raise
            
        return data
        
    def parse_category_page(self, html: str, base_url: str) -> Tuple[List[str], Optional[str]]:
        """Parse category page to extract listing URLs and next page URL.
        
        Args:
            html: HTML content of category page
            base_url: Base URL for resolving relative links
            
        Returns:
            Tuple of (list of listing URLs, next page URL or None)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        listing_urls = []
        next_page_url = None
        
        try:
            # Find all listing links
            # Andele uses specific class for listing cards
            listing_links = soup.find_all('a', href=re.compile(r'/perle/\d+/'))
            
            self.logger.debug(f"Found {len(listing_links)} raw links on page")
            
            seen_ids = set()
            for link in listing_links:
                href = link.get('href', '')
                if href:
                    full_url = urljoin(base_url, href)
                    listing_id = self._extract_listing_id(full_url)
                    
                    # Skip duplicates
                    if listing_id and listing_id not in seen_ids:
                        seen_ids.add(listing_id)
                        listing_urls.append(full_url)
                        self.logger.debug(f"Added listing: {listing_id}")
                    elif listing_id:
                        self.logger.debug(f"Duplicate skipped: {listing_id}")
                        
            # Find next page link
            next_page_url = self._extract_next_page(soup, base_url)
            
            self.logger.debug(f"Found {len(listing_urls)} listings, next page: {next_page_url}")
            
        except Exception as e:
            self.logger.error(f"Error parsing category page: {e}")
            
        return listing_urls, next_page_url
        
    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from URL.
        
        URL format: https://www.andelemandele.lv/perle/15757706/...
        """
        match = re.search(r'/perle/(\d+)/', url)
        if match:
            return match.group(1)
        return None
        
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract listing title."""
        # Try multiple selectors
        selectors = [
            'h1[itemprop="name"]',
            'h1.product-title',
            'h1',
            '[data-testid="listing-title"]',
            '.listing-title h1',
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                if title:
                    return title
                    
        # Fallback: try meta tag
        meta = soup.find('meta', property='og:title')
        if meta:
            return meta.get('content', 'Unknown Title')
            
        return 'Unknown Title'
        
    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price in EUR."""
        # Try multiple selectors
        price_selectors = [
            '[itemprop="price"]',
            '.price',
            '.listing-price',
            '[data-testid="price"]',
            '.product-price',
            '.current-price',
        ]
        
        for selector in price_selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True)
                price = self._parse_price_text(price_text)
                if price is not None:
                    return price
                    
        # Try meta tag
        meta = soup.find('meta', property='product:price:amount')
        if meta:
            try:
                return float(meta.get('content', '0'))
            except ValueError:
                pass
                
        return None
        
    def _parse_price_text(self, text: str) -> Optional[float]:
        """Parse price text to float."""
        # Remove currency symbols and whitespace
        text = text.replace('€', '').replace('EUR', '').replace(',', '.').strip()
        
        # Extract numbers
        match = re.search(r'[\d\s]+(?:\.\d{1,2})?', text)
        if match:
            try:
                # Remove spaces and convert
                price_str = match.group(0).replace(' ', '')
                return float(price_str)
            except ValueError:
                pass
                
        return None
        
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract listing description."""
        selectors = [
            '[itemprop="description"]',
            '.description',
            '.listing-description',
            '[data-testid="description"]',
            '.product-description',
            '#description',
            '.product-node__descr',  # Andele specific
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                # Get text and clean up
                text = elem.get_text(separator=' ', strip=True)
                if text:
                    return text
                
                # Check data-original attribute (sometimes used by Andele)
                data_original = elem.get('data-original', '')
                if data_original:
                    # Decode HTML entities if present
                    import html
                    decoded = html.unescape(data_original)
                    # Parse inner HTML
                    inner_soup = BeautifulSoup(decoded, 'html.parser')
                    text = inner_soup.get_text(separator=' ', strip=True)
                    if text:
                        return text
                    
        return None
        
    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from Andele listing page."""
        images = []
        
        # Andele uses <a> tags with href for gallery images
        gallery_links = soup.find_all('a', attrs={'data-trigger': 'gallery', 'data-role': 'gallery.pic'})
        for link in gallery_links:
            href = link.get('href', '')
            if href:
                if href not in images:
                    images.append(href)
        
        # Also try to extract from background-image in spans
        spans = soup.find_all('span', class_=re.compile(r'image-\d+'))
        for span in spans:
            style = span.get('style', '')
            # Extract URL from background-image:url('...')
            match = re.search(r"background-image:url\('([^']+)'\)", style)
            if match:
                url = match.group(1)
                if url and url not in images:
                    images.append(url)
        
        # Fallback: try other common selectors
        if not images:
            img_selectors = [
                '.gallery img',
                '.listing-images img',
                '.product-images img',
                '[data-testid="gallery-image"]',
                '.swiper-slide img',
                'img[itemprop="image"]',
                '.image-collage a',  # Andele specific
            ]
            
            for selector in img_selectors:
                elems = soup.select(selector)
                for elem in elems:
                    # Try href first (for <a> tags), then data-src, then src
                    src = elem.get('href') or elem.get('data-src') or elem.get('src', '')
                    if src:
                        # Make absolute URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = f"{self.BASE_URL}{src}"
                        if src not in images:
                            images.append(src)
        
        # Limit to first 5 images
        self.logger.debug(f"Extracted {len(images)} images: {images[:3]}")
        return images[:5]
        
    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract seller location."""
        selectors = [
            '[itemprop="addressLocality"]',
            '.location',
            '.seller-location',
            '[data-testid="location"]',
            '.listing-location',
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                location = elem.get_text(strip=True)
                if location:
                    return location
                    
        # Try to find in text
        location_patterns = [
            r'(?:Atrašanās vieta|Location|Vieta):\s*([^\n]+)',
            r'([A-ZĀČĒĢĪĶĻŅŌŖŠŪŽ][a-zāčēģīķļņōŗšūž]+(?:\s+[a-zāčēģīķļņōŗšūž]+){0,2})',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, soup.get_text())
            if match:
                return match.group(1).strip()
                
        return None
        
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract posting date."""
        # Try meta tags
        meta = soup.find('meta', property='article:published_time')
        if meta:
            try:
                date_str = meta.get('content', '')
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        # Try time element
        time_elem = soup.find('time')
        if time_elem:
            datetime_attr = time_elem.get('datetime')
            if datetime_attr:
                try:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                except ValueError:
                    pass
                    
        # Try specific selectors
        date_selectors = [
            '.listing-date',
            '.posted-date',
            '[data-testid="date"]',
            '.date-posted',
        ]
        
        for selector in date_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                date = self._parse_date_text(text)
                if date:
                    return date
                    
        return datetime.now()
        
    def _parse_date_text(self, text: str) -> Optional[datetime]:
        """Parse date from text."""
        # Common formats
        formats = [
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # 13.06.2026
            r'(\d{4})-(\d{2})-(\d{2})',  # 2026-06-13
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 13/06/2026
        ]
        
        for pattern in formats:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[2]) == 4:  # Year is last
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    return datetime(year, month, day)
                except (ValueError, IndexError):
                    pass
                    
        return None
        
    def _extract_next_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract next page URL from category page."""
        # Andele uses pagination with page numbers
        pagination_selectors = [
            '.pagination .next a',
            '.pagination a[rel="next"]',
            'a[rel="next"]',
            '.pager-next a',
            '[data-testid="next-page"]',
        ]
        
        for selector in pagination_selectors:
            elem = soup.select_one(selector)
            if elem:
                href = elem.get('href', '')
                if href:
                    return urljoin(base_url, href)
                    
        # Try to find numbered pagination
        pagination = soup.select_one('.pagination')
        if pagination:
            current = pagination.select_one('.active, .current')
            if current:
                # Find next number
                current_text = current.get_text(strip=True)
                try:
                    current_page = int(current_text)
                    next_page_link = pagination.select_one(f'a[href*="page={current_page + 1}"]')
                    if next_page_link:
                        return urljoin(base_url, next_page_link.get('href', ''))
                except (ValueError, TypeError):
                    pass
                    
        # Try to find any link that might be "next" page
        # Andele uses: first page (no suffix), second page (/page:1), third page (/page:2)
        current_page_match = re.search(r'page[:=](\d+)', base_url)
        # Extract current page number (0 = first page, 1 = second page, etc.)
        current_page = int(current_page_match.group(1)) if current_page_match else 0
        next_page_num = current_page + 1
        
        # Look for link with next page number
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Match page:N or page=N where N is next_page_num
            if f'page:{next_page_num}' in href or f'page={next_page_num}' in href:
                return urljoin(base_url, href)
                
        # Check for Vue.js / AJAX pagination buttons
        pagination_buttons = soup.select('[data-role="pagination"] a, .pagination a')
        for btn in pagination_buttons:
            text = btn.get_text(strip=True)
            if text == str(next_page_num) or 'next' in text.lower():
                href = btn.get('href', '')
                if href:
                    return urljoin(base_url, href)
                    
        return None
        
    def detect_category_from_title(self, title: str) -> str:
        """Detect category from title text.
        
        Used when parsing individual listings without context.
        """
        title_lower = title.lower()
        
        # GPU keywords
        if any(kw in title_lower for kw in ['rtx', 'gtx', 'rx ', 'radeon', 'geforce', 'grafikas', 'videokarte']):
            return 'gpu'
            
        # CPU keywords
        if any(kw in title_lower for kw in ['i3-', 'i5-', 'i7-', 'i9-', 'ryzen', 'core', 'processor', 'cpu']):
            return 'cpu'
            
        # SSD keywords
        if any(kw in title_lower for kw in ['ssd', 'nvme', 'm.2', 'sata', 'kingston', 'samsung', 'crucial', 'adata']) and 'dators' not in title_lower:
            if not any(kw in title_lower for kw in ['dators', 'pc', 'computer', 'komplektā']):
                return 'ssd'
                
        # RAM keywords
        if any(kw in title_lower for kw in ['ram', 'ddr3', 'ddr4', 'ddr5', 'atmiņa', 'hyperx', 'corsair']):
            if not any(kw in title_lower for kw in ['dators', 'pc', 'computer', 'komplektā']):
                return 'ram'
                
        # PSU keywords
        if any(kw in title_lower for kw in ['psu', 'barošanas', 'power supply', 'cooler master', 'be quiet', 'corsair rm', 'evga']):
            if not any(kw in title_lower for kw in ['dators', 'pc', 'computer', 'komplektā']):
                return 'psu'
                
        # Monitor keywords
        if any(kw in title_lower for kw in ['monitors', 'monitor', 'aoc', 'asus', 'lg', 'samsung', 'philips', '144hz', '240hz']):
            return 'monitor'
            
        # Motherboard keywords
        if any(kw in title_lower for kw in ['motherboard', 'mātesplate', 'b550', 'b450', 'x570', 'z690', 'z790']):
            return 'motherboard'
            
        return 'general'


# For testing
if __name__ == '__main__':
    import requests
    
    logging.basicConfig(level=logging.DEBUG)
    
    parser = AndeleParser()
    
    # Test URL
    test_url = "https://www.andelemandele.lv/perle/15757706/dell-wd19-dokstacija-ar-ladetaju-130-w-usb-c-4k/"
    
    try:
        response = requests.get(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        data = parser.parse_listing_page(response.text, test_url)
        
        print("\nParsed Listing:")
        print(f"ID: {data.listing_id}")
        print(f"Title: {data.title}")
        print(f"Price: €{data.price_eur}")
        print(f"Location: {data.seller_location}")
        print(f"Date: {data.date_posted}")
        print(f"Images: {len(data.image_urls)} found")
        print(f"Description: {data.description[:200]}..." if data.description and len(data.description) > 200 else f"Description: {data.description}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
