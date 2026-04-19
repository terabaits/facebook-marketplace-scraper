"""SSD listing parser for extracting data from HTML."""
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

from src.models.schemas import Listing
from src.utils.logger import get_logger

logger = get_logger("ssd_parser")


class SSDParser:
    """Parser for SSD listings from ss.com"""
    
    @staticmethod
    def parse_listing_page(html: str, listing_id: str, url: str) -> Optional[Listing]:
        """
        Parse an SSD listing page HTML.
        
        Args:
            html: Raw HTML content
            listing_id: The listing ID
            url: Full listing URL
            
        Returns:
            Listing object or None if parsing fails
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the main message div
            msg_div = soup.find('div', {'id': 'msg_div_msg'})
            if not msg_div:
                logger.warning(f"Could not find msg_div_msg for {listing_id}")
                return None
            
            # Extract title from the page title if available, otherwise from content
            title_elem = soup.find('title')
            title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""
            
            # Extract description text (before the table)
            description = ""
            for elem in msg_div.children:
                if elem.name and elem.name != 'table' and elem.name != 'div':
                    text = elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem).strip()
                    if text:
                        description = text
                        break
                elif elem.name == 'br':
                    continue
            
            # Parse the options table
            specs = SSDParser._parse_options_table(msg_div)
            
            # Extract price
            price = SSDParser._extract_price(msg_div)
            
            # Extract capacity from specs
            capacity_gb = None
            if 'Apjoms, Gb' in specs:
                try:
                    capacity_val = specs['Apjoms, Gb']
                    capacity_gb = int(capacity_val)
                except (ValueError, TypeError):
                    pass
            
            # Build title from brand + model if not found
            brand = specs.get('Marka', '')
            model = specs.get('Modelis', '')
            if not title or title == "":
                title = f"{brand} {model}".strip() if (brand or model) else "Unknown SSD"
            
            # Extract image URL
            image_url = None
            img_div = soup.find('div', {'id': 'content_sys_div_msg'})
            if img_div:
                img = img_div.find('img')
                if img and img.get('src'):
                    image_url = img['src']
                    if image_url.startswith('/'):
                        image_url = f"https://i.ss.com{image_url}"
            
            # Extract condition and model
            condition = specs.get('Stāvoklis', '')
            model_from_specs = specs.get('Modelis', '')
            brand_from_specs = specs.get('Marka', '')
            
            # Build full description with specs
            full_description = description
            if brand_from_specs:
                full_description += f"\nBrand: {brand_from_specs}"
            if model_from_specs:
                full_description += f"\nModel: {model_from_specs}"
            if condition:
                full_description += f"\nCondition: {condition}"
            
            # Build title from brand + model if not already present
            if not title or title == "":
                title = f"{brand_from_specs} {model_from_specs}".strip() if (brand_from_specs or model_from_specs) else "Unknown SSD"
            
            listing = Listing(
                listing_id=listing_id,
                title=title,
                description=full_description.strip(),
                price_eur=price,
                seller_location=None,
                listing_url=url,
                image_url=image_url,
                date_posted=None,
                category='ssd',
                capacity_gb=capacity_gb,
                is_active=True
            )
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing SSD listing {listing_id}: {e}")
            return None
    
    @staticmethod
    def _parse_options_table(msg_div) -> Dict[str, str]:
        """Parse the options table with SSD specs."""
        specs = {}
        
        # Find all tables with class options_list
        tables = msg_div.find_all('table', {'class': 'options_list'})
        
        for table in tables:
            # Find all rows in the table
            rows = table.find_all('tr')
            for row in rows:
                # Find cells with ads_opt_name (labels) and ads_opt (values)
                name_cell = row.find('td', {'class': 'ads_opt_name'})
                value_cell = row.find('td', {'class': 'ads_opt'})
                
                if name_cell and value_cell:
                    # Get the label text and clean it
                    label = name_cell.get_text(strip=True).rstrip(':')
                    # Get the value text (may be in bold)
                    value = value_cell.get_text(strip=True)
                    specs[label] = value
        
        return specs
    
    @staticmethod
    def _extract_price(msg_div) -> float:
        """Extract price from the listing."""
        # Look for the price table
        tables = msg_div.find_all('table')
        for table in tables:
            price_cell = table.find('td', {'class': 'ads_price'})
            if price_cell:
                price_text = price_cell.get_text(strip=True)
                # Extract numeric value
                price_match = re.search(r'([\d,]+)', price_text.replace(' ', ''))
                if price_match:
                    price_str = price_match.group(1).replace(',', '.')
                    try:
                        return float(price_str)
                    except ValueError:
                        pass
        
        return 0.0
    
    @staticmethod
    def extract_listing_urls(html: str, base_url: str = "https://www.ss.com") -> list:
        """
        Extract all listing URLs from a category page.
        
        Args:
            html: HTML content of the category page
            base_url: Base URL for constructing full URLs
            
        Returns:
            List of tuples (listing_id, full_url)
        """
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all links in the table rows
        rows = soup.find_all('tr')
        
        for row in rows:
            # Find links that point to message pages
            link = row.find('a', href=re.compile(r'/msg/'))
            if link:
                href = link.get('href', '')
                if '/msg/' in href:
                    # Extract listing ID from URL
                    match = re.search(r'/([a-z]+)\.html$', href)
                    if match:
                        listing_id = match.group(1)
                        full_url = href if href.startswith('http') else f"{base_url}{href}"
                        urls.append((listing_id, full_url))
        
        return urls
    
    @staticmethod
    def extract_pagination_info(html: str) -> dict:
        """Extract pagination information from category page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        info = {
            'current_page': 1,
            'total_pages': 1,
            'has_next': False,
            'next_url': None
        }
        
        # Find pagination div - try multiple selectors
        paging_div = soup.find('div', {'class': 'pagination'})
        
        # Alternative: look for paging links directly
        if not paging_div:
            # Look for "next" or "page" links in any div
            all_links = soup.find_all('a', href=re.compile(r'page\d+\.html|navig'))
            for link in all_links:
                href = link.get('href', '')
                if 'page' in href or 'navig' in href:
                    info['has_next'] = True
                    info['next_url'] = href if href.startswith('http') else f"https://www.ss.com{href}"
                    break
            return info
        
        # Extract current page
        current = paging_div.find('a', {'class': 'a_current'})
        if current:
            try:
                info['current_page'] = int(current.get_text(strip=True))
            except ValueError:
                pass
        
        # Find next page link
        next_link = paging_div.find('a', {'class': 'a_next'})
        if next_link and next_link.get('href'):
            info['has_next'] = True
            info['next_url'] = next_link['href']
        
        return info
