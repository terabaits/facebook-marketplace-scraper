"""RAM listing parser for extracting data from HTML."""
import re
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup

from src.models.schemas import Listing
from src.utils.logger import get_logger

logger = get_logger("ram_parser")


class RAMParser:
    """Parser for RAM listings from ss.com"""
    
    # Field name mappings (ss.com uses Latvian field names)
    FIELD_MAPPINGS = {
        # Capacity
        'Operatīvā atmiņa, Gb': 'capacity_gb',
        'Apjoms, Gb': 'capacity_gb',
        # Type (DDR3/DDR4/DDR5)
        'Tips': 'ram_type',
        'Veids': 'ram_type',
        'Operativas atminas tips': 'ram_type',
        # Frequency
        'Frekvence, MHz': 'frequency_mhz',
        'Atminas taktsfrekvence': 'frequency_mhz',
        'Frekvence': 'frequency_mhz',
        # Manufacturer
        'Ražotājs': 'manufacturer',
        'Marka': 'manufacturer',
        # Condition
        'Stāvoklis': 'condition',
        # Model
        'Modelis': 'model',
    }
    
    @staticmethod
    def parse_listing_page(html: str, listing_id: str, url: str) -> Optional[Listing]:
        """
        Parse a RAM listing page HTML.
        
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
            
            # Extract full description text from msg_div (excluding the table)
            description = ""
            for elem in msg_div.children:
                if elem.name == 'table':
                    continue  # Skip tables (options_list, etc.)
                if hasattr(elem, 'get_text'):
                    text = elem.get_text(strip=True)
                    if text:
                        description += text + " "
                elif isinstance(elem, str):
                    text = elem.strip()
                    if text:
                        description += text + " "
            description = description.strip()
            
            # Parse the options table
            specs = RAMParser._parse_options_table(msg_div)
            
            # Extract price
            price = RAMParser._extract_price(msg_div)
            
            # Extract specific RAM fields
            ram_fields = RAMParser._extract_ram_fields(specs)

            # Extract seller location from contacts table (e.g. Vieta / Pilsēta)
            seller_location = RAMParser._extract_seller_location(soup)

            # Extract image URL - prefer large .800 version over thumbnail
            image_url = None
            # ss.com puts gallery thumbnails in div#tr_foto with class pic_thumbnail
            tr_foto = soup.find('div', {'id': 'tr_foto'})
            if tr_foto:
                # find the large image or the first thumbnail
                large_img = tr_foto.find('img', {'id': 'msg_img_img'})
                if large_img and large_img.get('src'):
                    image_url = large_img['src']
                else:
                    img = tr_foto.find('img', {'class': 'pic_thumbnail'})
                    if img and img.get('src'):
                        image_url = img['src']
                        # Convert .t.jpg / .th2.jpg to .800.jpg full-size version
                        if image_url.endswith('.t.jpg'):
                            image_url = image_url[:-6] + '.800.jpg'
                        elif image_url.endswith('.th2.jpg'):
                            image_url = image_url[:-7] + '.800.jpg'
                if image_url and image_url.startswith('/'):
                    image_url = f"https://i.ss.com{image_url}"
            # Fallback to the old content_sys_div_msg path if needed
            if not image_url:
                img_div = soup.find('div', {'id': 'content_sys_div_msg'})
                if img_div:
                    img = img_div.find('img')
                    if img and img.get('src'):
                        image_url = img['src']
                        if image_url.startswith('/'):
                            image_url = f"https://i.ss.com{image_url}"
            
            # Build full description with specs
            full_description = description
            
            if ram_fields.get('manufacturer'):
                full_description += f"\nManufacturer: {ram_fields['manufacturer']}"
            if ram_fields.get('model'):
                full_description += f"\nModel: {ram_fields['model']}"
            if ram_fields.get('ram_type'):
                full_description += f"\nRAM Type: {ram_fields['ram_type']}"
            if ram_fields.get('frequency_mhz'):
                full_description += f"\nFrequency: {ram_fields['frequency_mhz']} MHz"
            if ram_fields.get('condition'):
                full_description += f"\nCondition: {ram_fields['condition']}"
            
            listing = Listing(
                listing_id=listing_id,
                title=title,
                description=full_description.strip(),
                price_eur=price,
                seller_location=seller_location,
                listing_url=url,
                image_url=image_url,
                date_posted=None,
                category='ram',
                capacity_gb=ram_fields.get('capacity_gb'),
                is_active=True
            )
            
            # Store additional RAM-specific fields for matching
            listing.ram_type = ram_fields.get('ram_type')
            listing.ram_frequency_mhz = ram_fields.get('frequency_mhz')
            listing.ram_manufacturer = ram_fields.get('manufacturer')
            listing.ram_model = ram_fields.get('model')
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing RAM listing {listing_id}: {e}")
            return None
    
    @staticmethod
    def _parse_options_table(msg_div) -> Dict[str, str]:
        """Parse the options table with RAM specs."""
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
                    label = name_cell.get_text(strip=True).rstrip(':').strip()
                    # Get the value text (may be in bold)
                    value = value_cell.get_text(strip=True)
                    specs[label] = value
        
        return specs
    
    @staticmethod
    def _extract_ram_fields(specs: Dict[str, str]) -> Dict[str, Any]:
        """Extract standardized RAM fields from specs dictionary."""
        fields = {
            'capacity_gb': None,
            'ram_type': None,
            'frequency_mhz': None,
            'manufacturer': None,
            'model': None,
            'condition': None,
        }
        
        for spec_name, spec_value in specs.items():
            # Normalize the field name
            normalized = RAMParser.FIELD_MAPPINGS.get(spec_name)
            if not normalized:
                continue
            
            value = spec_value.strip()
            
            if normalized == 'capacity_gb':
                try:
                    fields['capacity_gb'] = int(value)
                except (ValueError, TypeError):
                    pass
            
            elif normalized == 'ram_type':
                # Normalize DDR type (handle both digits and Roman numerals)
                # First try digits: DDR3, DDR4, DDR5
                ddr_match = re.search(r'DDR(\d+)', value, re.IGNORECASE)
                if ddr_match:
                    fields['ram_type'] = f"DDR{ddr_match.group(1)}"
                else:
                    # Try Roman numerals: DDR I, DDR II, DDR III, DDR IV, DDR V
                    roman_match = re.search(r'DDR\s*([IVX]+)', value, re.IGNORECASE)
                    if roman_match:
                        roman_to_digit = {'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5'}
                        roman_num = roman_match.group(1).upper()
                        if roman_num in roman_to_digit:
                            fields['ram_type'] = f"DDR{roman_to_digit[roman_num]}"
                        else:
                            fields['ram_type'] = value.upper() if value else None
                    else:
                        fields['ram_type'] = value.upper() if value else None
            
            elif normalized == 'frequency_mhz':
                try:
                    # Extract numeric value
                    freq_match = re.search(r'(\d+)', value)
                    if freq_match:
                        fields['frequency_mhz'] = int(freq_match.group(1))
                except (ValueError, TypeError):
                    pass
            
            elif normalized == 'manufacturer':
                fields['manufacturer'] = value
            
            elif normalized == 'model':
                fields['model'] = value
            
            elif normalized == 'condition':
                fields['condition'] = value
        
        return fields
    
    @staticmethod
    def _extract_seller_location(soup) -> Optional[str]:
        """Extract seller location from contacts table (Vieta / Pilsēta / Место / Place)."""
        try:
            # ss.com stores the contacts table in div#tr_cont, outside msg_div_msg
            tr_cont = soup.find('div', {'id': 'tr_cont'})
            search_tables = tr_cont.find_all('table') if tr_cont else soup.find_all('table')
            for table in search_tables:
                for row in table.find_all('tr'):
                    name_cell = row.find('td', {'class': 'ads_contacts_name'})
                    value_cell = row.find('td', {'class': 'ads_contacts'})
                    if name_cell and value_cell:
                        name = name_cell.get_text(strip=True).lower().rstrip(':')
                        # Latvian, Russian, English location labels
                        if name in (
                            'vieta', 'pilsēta', 'pilseta',
                            'atrašanās vieta', 'atrasanas vieta',
                            'место', 'город',
                            'place', 'location', 'city'
                        ):
                            return value_cell.get_text(strip=True)
        except Exception as e:
            logger.warning(f"Error extracting seller location: {e}")
        return None

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
