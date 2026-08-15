"""Console scraper for ss.com game console listings."""
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.scraper.crawler import Crawler
from src.models.schemas import ConsoleListing
from src.utils.config import AppConfig
from src.utils.logger import get_logger
from src.utils.listing_versioning import compute_content_fingerprint
from src.utils.image_downloader import ImageDownloader

logger = get_logger("console_scraper")


class ConsoleScraper(BaseScraper):
    """Scraper for ss.com game console listings."""
    
    # URLs to skip
    SKIP_PATTERNS = [
        'nopirkšu', 'pērku', 'remonts', 'internetveikals',
        'nopirksu', 'perku', 'remont', 'internet veikals',
        'veikals', 'īre', 'īres', 'iznomāt', 'emulators', 'emulatorus'
    ]
    
    def __init__(self, config: AppConfig, crawler: Optional[Crawler] = None):
        super().__init__(config, crawler)
        self.base_url = "https://www.ss.com"
        self.category_url = "/lv/electronics/computers/game-consoles/"
        self._stats = {
            'processed': 0,
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'matched': 0,
            'images_downloaded': 0,
        }
        self.image_downloader: Optional[ImageDownloader] = None
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/consoles")
    
    def scrape_category(self, max_pages: int = 0, limit: int = 0):
        """Scrape category pages."""
        return self.scrape_listings(
            max_pages=max_pages if max_pages > 0 else None,
            limit=limit if limit > 0 else None
        )
    
    def get_stats(self) -> dict:
        """Get scrape statistics."""
        return self._stats

    def scrape_listings(self, max_pages: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Scrape console listings from ss.com.
        
        Args:
            max_pages: Maximum number of pages to scrape (None for all)
            limit: Maximum number of listings to scrape (None for all)
        
        Returns:
            List of raw listing dictionaries
        """
        listings = []
        page_num = 1
        
        logger.info("Starting console listing scrape...")
        
        while True:
            # Check if we've reached the limit
            if limit and len(listings) >= limit:
                logger.info(f"Reached limit of {limit} listings")
                break
            
            if max_pages and page_num > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break
            
            url = self._get_page_url(page_num)
            logger.info(f"Fetching page {page_num}: {url}")
            
            response = self.crawler.fetch(url)
            if not response:
                logger.error(f"Failed to fetch page {page_num}")
                break
            
            soup = BeautifulSoup(response.html, 'html.parser')
            page_listings = self._parse_page(soup)
            
            if not page_listings:
                logger.info(f"No listings found on page {page_num}, stopping")
                break
            
            # Add listings up to the limit
            if limit:
                remaining = limit - len(listings)
                listings.extend(page_listings[:remaining])
                logger.info(f"Found {len(page_listings)} listings on page {page_num}, kept {min(len(page_listings), remaining)}")
                
                # Download images for new listings
                for listing in page_listings[:remaining]:
                    if listing.get('image_url') and self.image_downloader:
                        local_image_path = self.image_downloader.download_image(
                            listing['image_url'],
                            listing['listing_id']
                        )
                        if local_image_path:
                            self._stats['images_downloaded'] += 1
                            logger.info(f"Image saved locally: {local_image_path}")
            else:
                listings.extend(page_listings)
                logger.info(f"Found {len(page_listings)} listings on page {page_num}")
                
                # Download images for all listings
                for listing in page_listings:
                    if listing.get('image_url') and self.image_downloader:
                        local_image_path = self.image_downloader.download_image(
                            listing['image_url'],
                            listing['listing_id']
                        )
                        if local_image_path:
                            self._stats['images_downloaded'] += 1
                            logger.info(f"Image saved locally: {local_image_path}")
            
            # Check if we've reached the limit after adding
            if limit and len(listings) >= limit:
                break
            
            # Check for next page
            if not self._has_next_page(soup, page_num):
                break
            
            page_num += 1
        
        logger.info(f"Total listings scraped: {len(listings)}")
        return listings
    
    def _get_page_url(self, page_num: int) -> str:
        """Get URL for a specific page."""
        if page_num == 1:
            return f"{self.base_url}{self.category_url}"
        else:
            return f"{self.base_url}{self.category_url}page{page_num}.html"
    
    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there's a next page."""
        # Look for pagination links
        pagination = soup.find('div', class_='msga2') or soup.find('a', href=re.compile(r'page\d+\.html'))
        if not pagination:
            return False
        
        # Check if there's a link to current_page + 1
        next_page_pattern = rf'page{current_page + 1}\.html'
        return bool(soup.find('a', href=re.compile(next_page_pattern)))
    
    def _parse_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse all listings from a page."""
        listings = []
        seen_urls = set()  # Track URLs to avoid duplicates
        
        # Find all rows that contain message links (/msg/)
        # Console category uses different structure than GPU/CPU
        for row in soup.find_all('tr'):
            # Check if row has a link to a message
            link = row.find('a', href=re.compile(r'/msg/'))
            if not link:
                continue
            
            try:
                listing = self._parse_listing_row(row)
                if listing:
                    # Skip if we've already seen this URL
                    if listing['listing_url'] in seen_urls:
                        continue
                    seen_urls.add(listing['listing_url'])
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
        
        return listings
    
    def _parse_listing_row(self, row: BeautifulSoup) -> Optional[Dict]:
        """Parse a single listing row."""
        # Find all links in the row that go to /msg/
        msg_links = row.find_all('a', href=re.compile(r'/msg/'))
        if not msg_links:
            return None
        
        # Find the message link that has actual text (not just an image)
        # The first link is usually the thumbnail (just an image)
        # The second link has the actual title text
        msg_link = None
        for link in msg_links:
            text = link.get_text(strip=True)
            if text and len(text) > 10:  # Meaningful text, not just whitespace
                msg_link = link
                break
        
        # Fallback to first link if no text found
        if not msg_link and msg_links:
            msg_link = msg_links[0]
        
        if not msg_link:
            return None
        
        listing_url = msg_link['href']
        if not listing_url.startswith('/'):
            listing_url = '/' + listing_url
        
        full_url = f"{self.base_url}{listing_url}"
        
        # Extract title from the link
        title = msg_link.get_text(strip=True)
        
        # If no title, try span inside
        if not title:
            span = msg_link.find('span')
            if span:
                title = span.get_text(strip=True)
        
        # Check for skip patterns
        url_lower = full_url.lower()
        title_lower = title.lower() if title else ""
        
        for pattern in self.SKIP_PATTERNS:
            if pattern in url_lower or pattern in title_lower:
                logger.debug(f"Skipping listing with skip pattern '{pattern}': {full_url}")
                return None
        
        if not title:
            return None
        
        # Fetch detail page to get "Konsoles tips" (console type)
        detail_console_type = self._fetch_console_type(full_url)
        if detail_console_type:
            # Append console type to title for better matching
            title = f"{title} {detail_console_type}"
        
        # Extract price - look for price patterns in the row
        price = self._extract_price(row)
        
        # Extract location
        location = self._extract_location(row)
        
        # Extract date posted
        date_posted = self._extract_date(row)
        
        # Extract image URL
        image_url = self._extract_image(row)
        
        # Generate listing ID from URL
        listing_id = self._extract_listing_id(full_url)
        
        # Calculate content hash
        content_str = f"{title}|{price}|{location}"
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:32]
        
        return {
            'listing_id': listing_id,
            'title': title,
            'price_eur': price,
            'seller_location': location,
            'listing_url': full_url,
            'image_url': image_url,
            'date_posted': date_posted,
            'content_hash': content_hash,
            'raw_html': str(row)
        }
    
    def _extract_price(self, row: BeautifulSoup) -> float:
        """Extract price from listing row."""
        # Look for price patterns
        # ss.com typically shows prices in elements with specific classes
        price_patterns = [
            (r'(\d+[\s,]*\d*)\s*€', 'eur'),
            (r'€\s*(\d+[\s,]*\d*)', 'eur'),
            (r'(\d+[\s,]*\d*)\s*EUR', 'eur'),
        ]
        
        text = row.get_text()
        
        for pattern, currency in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(' ', '').replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        # Try to find price in any td element
        tds = row.find_all('td')
        for td in tds:
            text = td.get_text(strip=True)
            # Look for numeric values that look like prices
            price_match = re.search(r'(\d{2,4})[\s,]*(-|\s)', text)
            if price_match:
                try:
                    return float(price_match.group(1))
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_location(self, row: BeautifulSoup) -> Optional[str]:
        """Extract seller location from listing row."""
        # Look for location patterns
        location_patterns = [
            r'(Rīga|Jūrmala|Ogre|Ķekava|Valmiera|Liepāja|Daugavpils|Ventspils|Jelgava)',
        ]
        
        text = row.get_text()
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_date(self, row: BeautifulSoup) -> Optional[datetime]:
        """Extract date posted from listing row."""
        text = row.get_text()
        
        # Look for date patterns
        date_patterns = [
            r'(\d{2})\.(\d{2})\.(\d{4})',
            r'(\d{2})\.(\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 3:
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    else:
                        day, month = match.groups()
                        year = datetime.now().year
                        return datetime(year, int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def _extract_image(self, row: BeautifulSoup) -> Optional[str]:
        """Extract image URL from listing row and convert to full size."""
        # Prefer full-size gallery image from a thumbnail link
        thumb_link = row.find('a', href=re.compile(r'/gallery/|/i\.ss\.com/', re.I))
        if thumb_link:
            href = thumb_link.get('href')
            if href:
                if href.startswith('/'):
                    href = f"https://i.ss.com{href}"
                return href

        # Fallback: find any img and convert common thumbnail suffixes
        img = row.find('img')
        if img and img.get('src'):
            src = img['src']
            if src.startswith('/'):
                src = f"https://i.ss.com{src}"

            # Convert thumbnail URL to full size. ss.com search results use
            # .t.jpg or .th2.jpg thumbnails; the full-size gallery image is
            # the same base name with .800.jpg. Replace the whole suffix to
            # avoid double dots like "123..800.jpg".
            full_src = src.replace('.thumb.', '.').replace('.th.', '.')
            full_src = re.sub(r'\.t\.jpg$', '.800.jpg', full_src)
            full_src = re.sub(r'\.th2\.jpg$', '.800.jpg', full_src)
            return full_src

        return None
    
    def _extract_listing_id(self, url: str) -> str:
        """Extract unique listing ID from URL."""
        # ss.com URLs typically contain an ID like /msg/lv/electronics/.../ID.html
        match = re.search(r'/(\d+)\.html$', url)
        if match:
            return f"ss_{match.group(1)}"
        
        # Fallback: hash the URL
        return f"ss_{hashlib.md5(url.encode()).hexdigest()[:12]}"
    
    def fetch_description(self, listing_url: str) -> str:
        """Fetch full description from listing detail page."""
        try:
            response = self.crawler.fetch(listing_url)
            if not response:
                return ""
            
            soup = BeautifulSoup(response.html, 'html.parser')
            
            # Find description - typically in a specific div
            desc_div = soup.find('div', class_='msg_body') or soup.find('div', id='msg_div_msg')
            if desc_div:
                return desc_div.get_text(strip=True, separator=' ')
            
            # Fallback: get all text
            return soup.get_text(strip=True, separator=' ')[:1000]
        
        except Exception as e:
            logger.error(f"Error fetching description from {listing_url}: {e}")
            return ""
    
    def _fetch_console_type(self, listing_url: str) -> Optional[str]:
        """Fetch console type from detail page 'Konsoles tips' field."""
        try:
            response = self.crawler.fetch(listing_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.html, 'html.parser')
            
            # Look for "Konsoles tips:" row
            for row in soup.find_all('tr'):
                label = row.find('td', class_='ads_opt_name')
                if label and 'konsoles' in label.get_text(strip=True).lower():
                    value = row.find('td', class_='ads_opt')
                    if value:
                        return value.get_text(strip=True)
            
            return None
        except Exception as e:
            logger.error(f"Error fetching console type from {listing_url}: {e}")
            return None
