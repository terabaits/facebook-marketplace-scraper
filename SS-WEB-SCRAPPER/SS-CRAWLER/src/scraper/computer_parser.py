"""Parser for computer listings from ss.com."""
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from bs4 import BeautifulSoup

from src.models.schemas import Listing
from src.utils.text import normalize_text, compute_content_hash
from src.utils.logger import get_logger

logger = get_logger("computer_parser")


# Skip patterns - listings to exclude
SKIP_PATTERNS = [
    "pērku", "multisistēma rīga", "jaunaka", "veikals",
    "garantija 2 gadi", "remonts",
    "piegādi visā latvijā", "piegāde visā latvijā",
    "mājas lapā", "mac", "imac",  # Skip Apple Mac/iMac listings (not PC components)
    "all-in-one", "all in one",  # Skip All-In-One computers (monitors with built-in components)
    # Service/shop listings that look like PC ads but are not actual hardware for sale
    "planšetdators",           # Tablet listings miscategorized as computers
    "pieņemam",                # "We accept/buy" service ads
    "atjaunotus datorus ar garantiju",  # Refurbished computers with warranty (shop/service)
    "garantija: 6 mēneši",     # Generic 6-month warranty used by refurb resellers
]


class ComputerComponentExtractor:
    """Extract PC components from listing text."""

    def __init__(self):
        # CPU patterns
        self.cpu_patterns = [
            # Intel patterns
            r'i[3579][-\s]?\d{3,5}[kft]?',  # i7-14700, i9-14900K, etc.
            r'core[\s]?i[3579]',  # Core i7
            r'xeon[\s]?[ew]?[\s]?\d[-\s]?\d{4}',  # Xeon E5-2680, etc.
            r'pentium[\s]?\w+',  # Pentium Gold, etc.
            r'celeron[\s]?\w+',  # Celeron
            # AMD patterns
            r'ryzen[\s]?\d?[\s]?\d{4}[xgt]?',  # Ryzen 5 5600X, Ryzen 7 7800X
            r'ryzen[\s]?\d',  # Ryzen 5, Ryzen 7
            r'athlon[\s]?\w+',  # Athlon
            r'fx[\s-]?\d+',  # FX-8350
            r'a[\s-]?\d+[\s-]?\d+',  # A10-6800K
            # Generic
            r'amd[\s]?(?:ryzen[\s]?)?[3579]?[\s]?\d{4}[xgt]?',  # AMD 5 9600X, AMD 9600X
            r'amd[\s]?\d{4}',  # AMD 5600
            r'intel[\s]?\w+',  # Intel variants
        ]

        # GPU patterns
        self.gpu_patterns = [
            # NVIDIA
            r'rtx[\s]?\d{4}[\s]?ti?',  # RTX 4090, RTX 3060 Ti
            r'gtx[\s]?\d{3,4}[\s]?ti?',  # GTX 1080 Ti
            r'gt[\s]?\d{3}',  # GT 1030
            r'quadro[\s]?\w+',  # Quadro
            # AMD
            r'rx[\s]?\d{4}[\s]?xt?',  # RX 7800 XT
            r'radeon[\s]?\(?tm\)?[\s]?r9[\s]?\d{2,3}[a-z]?',  # Radeon (tm) R9 390
            r'radeon[\s]?\w+',  # Radeon RX
            r'vega[\s]?\d+',  # Vega 56/64
            # Intel
            r'arc[\s]?a?\d+',  # Arc A770
            # Generic patterns for extraction
            r'nvidia[\s]?\w+',
            # Removed r'amd[\s]?\w+' because it falsely matched AMD CPU text
            # (e.g., "AMD 5 9600X" as GPU "amd 5"). AMD GPU models are already
            # covered by rx/radeon/vega patterns above.
        ]

        # Motherboard patterns
        self.motherboard_patterns = [
            r'pamat\s*plate\s*:\s*([A-Za-z0-9][A-Za-z0-9\s\-/]*)',
            r'mātesplate\s*:\s*([A-Za-z0-9][A-Za-z0-9\s\-/]*)',
            r'motherboard\s*:\s*([A-Za-z0-9][A-Za-z0-9\s\-/]*)',
            r'\b([a-z]\d{2,3}[-]gaming[-]?\d?)\b',  # e.g., AX370-Gaming 3
            r'\b([a-z]\d{2,3}[-]?gaming[-]?plus)\b',
            r'\b([a-z]\d{2,3}[-]?tomahawk)\b',
        ]

        # RAM patterns
        self.ram_patterns = [
            r'\d{1,2}[\s]?gb[\s]?ram',
            r'\d{1,2}[\s]?gb[\s]?ddr[\d]?',
            r'ddr[\d][\s-]?\d{4}',  # DDR4-3200
            r'\d{1,2}[\s]?gb[\s]?\(\d+x\d+gb\)',  # 16GB (2x8GB)
            r'\d{1,2}gb',  # 16GB
            r'16[\s]?gb', r'32[\s]?gb', r'64[\s]?gb', r'8[\s]?gb',
            r'ram[\s]?\d+',
        ]

        # SSD patterns
        self.ssd_patterns = [
            r'\d{3,4}[\s]?gb[\s]?ssd',
            r'\d+[\s]?tb[\s]?ssd',
            r'ssd[\s]?\d+[\s]?gb',
            r'ssd[\s]?\d+[\s]?tb',
            r'nvme[\s]?\d+[\s]?gb',
            r'm\.2[\s]?\d+[\s]?gb',
            r'\d+[\s]?gb[\s]?nvme',
            r'256[\s]?gb', r'512[\s]?gb', r'1024[\s]?gb', r'1[\s]?tb',
            r'2[\s]?tb', r'2000[\s]?gb', r'4[\s]?tb',
        ]

        # PSU patterns
        self.psu_patterns = [
            r'\d{3,4}[\s]?w',  # 750W, 650W
            r'psu[\s]?\d{3}',  # PSU 750
            r'barošana[\s]?\d{3}',  # Barošana 750 (Latvian)
        ]

        # Case patterns
        self.case_patterns = [
            r'korpuss[\s]?\w+',  # Korpuss + model
            r'korpuss\b',  # Just korpuss
            r'tower\b',
            r'midi[\s-]?tower',
            r'mini[\s-]?tower',
            r'full[\s-]?tower',
            r'case\b',
            r'fractal[\s]?\w+',
            r'nzxt[\s]?\w+',
            r'corsair[\s]?\w+',
        ]

        # Monitor patterns
        self.monitor_patterns = [
            r'\d{2}[\s]?"[\s]?monitors',  # 24" monitors
            r'monitors[\s]?\d{2}',  # monitors 24
            r'\d{2}[\s]?collu',  # 24 collu (inches in Latvian)
            r'display\b',
            r'ekrāns[\s]?\d{2}',  # ekrāns 24 (screen in Latvian)
        ]

    def extract_components(self, text: str) -> Dict[str, List[str]]:
        """Extract all component mentions from text."""
        normalized = normalize_text(text.lower())
        components = {
            'cpu': [],
            'gpu': [],
            'ram': [],
            'ssd': [],
            'motherboard': [],
            'psu': [],
            'case': [],
            'monitor': []
        }

        seen = set()  # Track seen matches to avoid duplicates

        # Extract CPU
        for pattern in self.cpu_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['cpu'].append(match.strip())
                    seen.add(match_clean)

        # Extract GPU
        for pattern in self.gpu_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['gpu'].append(match.strip())
                    seen.add(match_clean)

        # Extract RAM
        for pattern in self.ram_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen and len(match_clean) > 1:
                    components['ram'].append(match.strip())
                    seen.add(match_clean)

        # Extract SSD
        for pattern in self.ssd_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['ssd'].append(match.strip())
                    seen.add(match_clean)

        # Extract PSU
        for pattern in self.psu_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['psu'].append(match.strip())
                    seen.add(match_clean)

        # Extract Case
        for pattern in self.case_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['case'].append(match.strip())
                    seen.add(match_clean)

        # Extract Monitor
        for pattern in self.monitor_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_clean = match.lower().replace(' ', '').replace('-', '')
                if match_clean not in seen:
                    components['monitor'].append(match.strip())
                    seen.add(match_clean)

        # Extract Motherboard
        for pattern in self.motherboard_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                mb_text = match.group(1).strip() if match.lastindex else match.group(0).strip()
                match_clean = mb_text.lower().replace(' ', '').replace('-', '')
                if len(mb_text) >= 3 and match_clean not in seen:
                    components['motherboard'].append(mb_text)
                    seen.add(match_clean)

        return components

    def has_gpu(self, text: str) -> bool:
        """Check if text mentions a GPU."""
        normalized = normalize_text(text.lower())
        for pattern in self.gpu_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False

    def has_psu(self, text: str) -> bool:
        """Check if text mentions a PSU."""
        normalized = normalize_text(text.lower())
        for pattern in self.psu_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False

    def has_case(self, text: str) -> bool:
        """Check if text mentions a case."""
        normalized = normalize_text(text.lower())
        for pattern in self.case_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False


class ComputerListingParser:
    """Parse ss.com computer listing HTML into structured data."""

    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'html.parser')
        self.listing_id = self._extract_listing_id(url)
        self.extractor = ComputerComponentExtractor()

    def _extract_listing_id(self, url: str) -> str:
        """Extract listing ID from URL."""
        match = re.search(r'/([a-z0-9]+)\.html$', url)
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

    def _extract_price(self) -> Optional[float]:
        """Extract price from price element."""
        price_elem = self.soup.select_one('.ads_price')
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
        desc_elem = self.soup.select_one('#msg_div_msg')
        if not desc_elem:
            return None

        text_parts = []

        # First, get all the raw text including free-form description
        # This captures text like "4x Kingston HyperX Fury Black 8GB 2666MHz"
        raw_text = desc_elem.get_text(separator='\n', strip=True)
        if raw_text:
            text_parts.append(raw_text)

        # Then also extract structured data from tables for component matching
        for child in desc_elem.children:
            if child.name == 'div' and 'float' in child.get('style', ''):
                continue
            if child.name == 'table':
                # Include options_list tables - they contain component specs!
                if child.find('img'):
                    continue
                # Extract text from options_list for component matching
                if 'options_list' in child.get('class', []):
                    # Get all option values (second column) WITH their labels for context
                    rows = child.find_all('tr')
                    option_lines = []
                    for row in rows:
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            # Include both label and value for better context
                            label_text = tds[0].get_text(strip=True).lower()
                            value_text = tds[1].get_text(strip=True)
                            if value_text:
                                # Combine label and value (e.g., "operativa atmina gb: 16")
                                full_text = f"{label_text}: {value_text}"
                                option_lines.append(full_text)
                    # Merge CPU frequency with CPU model when CPU lacks specific model number
                    # e.g. "Procesors: Amd ryzen 5" + "Procesora frekvence, Ghz: 3.60"
                    for i, line in enumerate(option_lines):
                        if re.search(r'procesors?:\s*amd\s+ryzen\s+\d+(?!\s*\d{3,4})', line, re.IGNORECASE):
                            # CPU has Ryzen series but no 4-digit model; look for nearby frequency
                            for j in range(i+1, min(i+4, len(option_lines))):
                                freq_match = re.search(r'frekvence.*?ghz\s*:\s*(\d+\.\d+)', option_lines[j], re.IGNORECASE)
                                if freq_match:
                                    option_lines[i] = f"{line} {freq_match.group(1)}"
                                    break

                    # Add each option as separate line for context-based matching
                    for line in option_lines:
                        text_parts.append(line)
                    continue

        result = '\n'.join(text_parts) if text_parts else None
        if result:
            # Remove common trademark/registration symbols that break component extraction
            result = re.sub(r'[™®©]', '', result)
            result = re.sub(r'\(tm\)|\(r\)|\(c\)', '', result, flags=re.IGNORECASE)
            # Merge "Ryzen 5" with nearby GHz value so the CPU matcher can disambiguate
            result = re.sub(
                r'(?i)(procesors?:\s*(?:amd\s+)?ryzen\s+\d+)(?:\s*\n\s*procesora\s+frekvence,?\s*ghz:\s*(\d+\.\d+))?',
                lambda m: f'{m.group(1)} {m.group(2)}' if m.group(2) else m.group(1),
                result
            )
        return result

    def _extract_date(self) -> Optional[datetime]:
        """Extract date from footer."""
        for td in self.soup.select('td.msg_footer'):
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

    def _extract_seller_company(self) -> Optional[str]:
        """Extract seller company name from contacts table."""
        for td in self.soup.select('td.ads_contacts_name'):
            label = td.get_text(strip=True)
            if 'Uzņēmums' in label or 'Company' in label or 'Pārdevējs' in label:
                value_td = td.find_next_sibling('td', class_='ads_contacts')
                if value_td:
                    return value_td.get_text(strip=True)
        return None

    def _extract_location(self) -> Optional[str]:
        """Extract seller location from contacts."""
        for td in self.soup.select('td.ads_contacts_name'):
            label = td.get_text(strip=True)
            if 'Vieta' in label:
                value_td = td.find_next_sibling('td', class_='ads_contacts')
                if value_td:
                    # Get text but filter out phone number UI elements
                    full_text = value_td.get_text(strip=True)
                    # Split by newlines and take only the first line (the actual location)
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    for line in lines:
                        # Skip lines that look like phone numbers or contain "tālruni" (phone)
                        if not re.search(r'\(\+\d+\)|tālruni|Parādīt', line, re.IGNORECASE):
                            return line
        return None

    def _extract_image(self) -> Optional[str]:
        """Extract main image URL and convert to full size."""
        img = self.soup.select_one('img.pic_thumbnail')
        if not img:
            return None

        # ss.com wraps the thumbnail in an <a> tag pointing to the full image (.800.jpg)
        parent_a = img.find_parent('a')
        if parent_a:
            href = parent_a.get('href')
            if href and ('.jpg' in href or '.jpeg' in href or '.png' in href):
                if href.startswith('//'):
                    return f"https:{href}"
                elif href.startswith('/'):
                    return f"https://www.ss.com{href}"
                else:
                    return href

        # Fallback: derive full image from thumbnail src
        src = img.get('src') or img.get('data-src')
        if src:
            if src.startswith('//'):
                src = f"https:{src}"
            elif src.startswith('/'):
                src = f"https://www.ss.com{src}"
            # Convert thumbnail URL to full size
            full_src = src.replace('.thumb.', '.').replace('.th.', '.').replace('.t.', '.800.')
            return full_src
        return None

    def should_skip(self, title: str, description: str = "", seller: str = "") -> Tuple[bool, str]:
        """Check if listing should be skipped based on filter rules."""
        full_text = f"{title} {description} {seller}".lower()

        for pattern in SKIP_PATTERNS:
            if pattern.lower() in full_text:
                return True, f"Contains skip pattern: '{pattern}'"

        return False, ""

    def parse(self) -> Optional[Listing]:
        """Parse HTML into Listing object."""
        # Get title from h2 or fallback
        title_elem = self.soup.select_one('h2')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        description = self._extract_description()

        # Extract seller/company early so skip patterns can catch shop names
        seller = self._extract_seller_company() or ""

        # Check skip patterns
        should_skip, skip_reason = self.should_skip(title, description or "", seller)
        if should_skip:
            logger.info(f"Skipping listing {self.listing_id}: {skip_reason}")
            return None

        price = self._extract_price()
        if price is None:
            logger.warning(f"No price found for {self.url}")
            price = 0.0

        date_posted = self._extract_date()
        location = self._extract_location()
        image_url = self._extract_image()

        content_hash = compute_content_hash(title, price, location or "")

        return Listing(
            listing_id=self.listing_id,
            title=title,
            description=description,
            price_eur=price,
            seller_location=location,
            listing_url=self.url,
            image_url=image_url,
            date_posted=date_posted,
            content_hash=content_hash,
            category='computer'
        )

    def get_category_links(self) -> List[str]:
        """Extract all listing links from category page."""
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
        """Check for pagination and return next page URL if exists."""
        next_link = self.soup.find('a', text=re.compile(r'Nākošie'))
        if next_link:
            href = next_link.get('href')
            if href:
                if href.startswith('/'):
                    return f"https://www.ss.com{href}"
                return href
        return None