"""SSD listing parser for extracting data from HTML."""
import re
from datetime import datetime
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

            # Extract rich HTML description from the message div.
            # Includes full inner HTML of msg_div_msg (images, line breaks, etc.)
            # minus the floating image container, plus a readable spec summary.
            description = SSDParser._extract_full_description(msg_div, include_html=False)

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

            # Extract date from the page footer (same pattern as GPU/CPU parsers)
            date_posted = SSDParser._extract_date(soup)

            # Extract image URL
            # ss.com puts the primary listing photo in an <img class="pic_thumbnail isfoto">
            # inside #content_sys_div_msg. Search several selectors for robustness and
            # convert thumbnail URLs to full-size images.
            image_url = None

            def _make_absolute(src: str) -> str:
                if not src:
                    return src
                if src.startswith('//'):
                    return f"https:{src}"
                if src.startswith('/'):
                    return f"https://i.ss.com{src}"
                return src

            def _extract_img_src(container) -> Optional[str]:
                if not container:
                    return None
                # If the container is itself an <img>, return its src directly.
                if getattr(container, 'name', None) == 'img':
                    return container.get('src') or container.get('data-src')
                for img in container.find_all('img'):
                    classes = img.get('class') or []
                    if any(c in classes for c in ('pic_thumbnail', 'isfoto')):
                        return img.get('src') or img.get('data-src')
                img = container.find('img')
                return img.get('src') or img.get('data-src') if img else None

            for tag, kwargs in [
                ('div', {'id': 'content_sys_div_msg'}),
                ('img', {'class_': 'pic_thumbnail'}),
                ('img', {'class_': 'isfoto'}),
                ('div', {'id': 'msg_div_msg'}),
            ]:
                elem = soup.find(tag, **kwargs)
                if elem is None:
                    continue
                # Use the matched element as container; for divs search inside, for img use itself.
                src = _extract_img_src(elem)
                if src:
                    image_url = _make_absolute(src)
                    break

            # Convert thumbnail/preview to full-size image if applicable.
            # IMPORTANT: for ss.com gallery URLs:
            #   .t.jpg   = real thumbnail (usable)
            #   .800.jpg = real full-size image
            #   .jpg     = 1px placeholder (must avoid)
            if image_url:
                is_ss_gallery = '/i.ss.com/gallery/' in image_url or image_url.startswith('https://i.ss.com/gallery/')
                if is_ss_gallery:
                    if image_url.endswith('.t.jpg'):
                        # Use the full-size gallery image
                        image_url = image_url[:-6] + '.800.jpg'
                else:
                    if image_url.endswith('.t.jpg'):
                        image_url = image_url[:-6] + '.jpg'
                    image_url = image_url.replace('.thumb.', '.').replace('.th.', '.')
                    # ss.com sometimes serves a small preview with dimensions in path like /120x90/
                    dim_match = re.search(r'/(\d{2,4}x\d{2,4})/', image_url)
                    if dim_match:
                        image_url = image_url.replace('/' + dim_match.group(1) + '/', '/')
                    # Some galleries use /s/ prefix for small; remove it.
                    image_url = re.sub(r'(?<=/)s(?=/)', '', image_url)

            # Extract condition and model
            condition = specs.get('Stāvoklis', '')
            model_from_specs = specs.get('Modelis', '')
            brand_from_specs = specs.get('Marka', '')

            # The full description already contains all specs as readable lines,
            # so we no longer need to manually append a duplicate subset here.
            full_description = description

            # Sanitize title: remove redundant ss.com prefix/category path.
            # Prefer "Brand Model ..." from the description text when available.
            clean_title = title
            if title.startswith('SS.COM'):
                # Try to build a more useful title from the first text line of the description
                # or from brand + model specs.
                if description:
                    first_text_line = re.sub(r'<[^>]+>', '', description).split('\n')[0].strip()
                    # Use first text line if it contains a likely product/model name
                    if first_text_line and not first_text_line.lower().startswith('marka:'):
                        clean_title = first_text_line[:200]
                if (not clean_title or clean_title.startswith('SS.COM')) and (brand_from_specs or model_from_specs):
                    clean_title = f"{brand_from_specs} {model_from_specs}".strip()
                    if clean_title:
                        # Append first description snippet to add context, without duplicating brand/model
                        first_text_line = re.sub(r'<[^>]+>', '', description or '').split('\n')[0].strip()
                        if first_text_line and brand_from_specs.lower() not in first_text_line.lower():
                            extra = first_text_line
                            if len(extra) > 60:
                                extra = extra[:60].rsplit(' ', 1)[0] + '...'
                            clean_title = f"{clean_title} - {extra}"
            title = clean_title if clean_title else title

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
                date_posted=date_posted,
                category='ssd',
                capacity_gb=capacity_gb,
                is_active=True
            )

            return listing

        except Exception as e:
            logger.error(f"Error parsing SSD listing {listing_id}: {e}")
            return None

    @staticmethod
    def _extract_full_description(msg_div, include_html: bool = False) -> str:
        """
        Build a rich description from #msg_div_msg.

        Returns a cleaned plain-text summary: free-form listing text, spec table
        rows as "Label: Value", and the human-readable price. HTML tags are
        stripped so descriptions display cleanly in the UI and database.

        The floating image container (#content_sys_div_msg) is excluded from the
        text because the image is stored separately in image_url.
        """
        parts = []

        # 1. Free-form description text (exclude image div and spec/price tables)
        msg_clone = BeautifulSoup(str(msg_div), 'html.parser').find('div', {'id': 'msg_div_msg'})
        if msg_clone:
            image_div = msg_clone.find('div', id='content_sys_div_msg')
            if image_div:
                image_div.decompose()
            for table in msg_clone.find_all('table'):
                table.decompose()
            for br in msg_clone.find_all('br'):
                br.replace_with('\n')
            free_text = msg_clone.get_text(separator='\n', strip=True)
            free_text = re.sub(r'[ \t]+', ' ', free_text)
            free_text = re.sub(r'\n{3,}', '\n\n', free_text).strip()
            if free_text:
                parts.append(free_text)

        # 2. Options tables -> "Label: Value" lines
        # Use a set to deduplicate because ss.com nests tables.
        seen_spec_lines = set()
        spec_lines = []
        for table in msg_div.find_all('table', {'class': 'options_list'}):
            for row in table.find_all('tr'):
                # Only use rows that directly contain both label and value cells,
                # ignoring nested inner-table rows that duplicate data.
                name_cell = row.find('td', {'class': 'ads_opt_name'}, recursive=False)
                value_cell = row.find('td', {'class': 'ads_opt'}, recursive=False)
                if not name_cell or not value_cell:
                    cells = row.find_all('td', recursive=False)
                    if len(cells) >= 2:
                        name_cell = cells[0] if 'ads_opt_name' in (cells[0].get('class') or []) else None
                        value_cell = cells[1] if 'ads_opt' in (cells[1].get('class') or []) else None
                if name_cell and value_cell:
                    label = name_cell.get_text(strip=True).rstrip(':').strip()
                    value = value_cell.get_text(strip=True)
                    if label and value:
                        line = f"{label}: {value}"
                        if line not in seen_spec_lines:
                            seen_spec_lines.add(line)
                            spec_lines.append(line)
        if spec_lines:
            parts.append("\n".join(spec_lines))

        # 3. Price table - use the raw human-readable price text
        for table in msg_div.find_all('table'):
            price_cell = table.find('td', {'class': 'ads_price'})
            if price_cell:
                price_text = price_cell.get_text(strip=True)
                if price_text:
                    parts.append(f"Cena: {price_text}")
                break

        return '\n'.join(parts)

    @staticmethod
    def _extract_date(soup: BeautifulSoup) -> Optional[datetime]:
        """Extract the posting date from the page footer (Datums: DD.MM.YYYY HH:MM)."""
        # ss.com places the date in a td with class msg_footer; prefer that first.
        for cls in ['msg_footer', 'msg_footer2']:
            for td in soup.find_all('td', class_=cls):
                text = td.get_text(strip=True)
                match = re.search(r'Datums:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', text)
                if match:
                    day, month, year, hour, minute = match.groups()
                    try:
                        return datetime(int(year), int(month), int(day), int(hour), int(minute))
                    except ValueError:
                        pass
        # Fallback: scan all tds for the date pattern.
        for td in soup.find_all('td'):
            text = td.get_text(strip=True)
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
