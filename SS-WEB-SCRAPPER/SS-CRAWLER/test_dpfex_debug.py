"""Debug dpfex.html - check raw text and matching"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper
from src.utils.text import normalize_text
import re

config = AppConfig.from_yaml()
config.scraper.test_mode = True

scraper = ComputerScraper(config)
scraper.initialize()

url = "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"

# Fetch raw HTML
from src.scraper.crawler import Crawler
crawler = Crawler(config)
html = crawler.fetch(url)

# Parse with ComputerListingParser
from src.scraper.parsers.computer_parser import ComputerListingParser
parser = ComputerListingParser(html, url)
base_listing = parser.parse()

print("=== RAW TEXT ===")
print(f"Title: {base_listing.title}")
print(f"\nDescription:\n{base_listing.description}")

print("\n=== NORMALIZED TEXT ===")
normalized = normalize_text(base_listing.title + " " + (base_listing.description or ""))
print(normalized[:1000])

print("\n=== SSD EXTRACTION ===")
text_lower = (base_listing.title + " " + (base_listing.description or "")).lower()

# Check for SSD patterns
ssd_patterns = [
    r'(\d{3,4})\s*gb\s+(?:ssd|nvme|m\.2)',
    r'(?:ssd|nvme|m\.2)\s+(\d{3,4})\s*gb',
    r'ssd\s*[:\-]?\s*(\d{3,4})\s*gb',
]

for pattern in ssd_patterns:
    matches = list(re.finditer(pattern, text_lower))
    print(f"Pattern '{pattern}': {len(matches)} matches")
    for m in matches:
        print(f"  - Capacity: {m.group(1)}GB at position {m.start()}")
        # Show context
        start = max(0, m.start() - 30)
        end = min(len(text_lower), m.end() + 30)
        print(f"    Context: ...{text_lower[start:end]}...")

print("\n=== MONITOR EXTRACTION ===")
# Check for monitor patterns
monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays', 'hp']
for kw in monitor_keywords:
    if kw in text_lower:
        # Find all occurrences
        for match in re.finditer(kw, text_lower):
            start = max(0, match.start() - 50)
            end = min(len(text_lower), match.end() + 50)
            print(f"Found '{kw}' at {match.start()}: ...{text_lower[start:end]}...")

print("\n=== ATTEMPTING SSD MATCH ===")
# Try SSD matching
full_text = base_listing.title + " " + (base_listing.description or "")
match_result = scraper.matcher.match(
    base_listing.title,
    base_listing.description or "",
    base_listing.price_eur
)

if match_result.ssd:
    print(f"SSD matched: {match_result.ssd}")
    print(f"SSD method: {match_result.ssd_method}")
else:
    print("No SSD matched")

# Check what _extract_ssd_capacity finds
ssd_capacity = scraper.matcher._extract_ssd_capacity(full_text)
print(f"Extracted SSD capacity: {ssd_capacity}")

print("\n=== CHECKING HP MONITOR MODELS ===")
# Search for HP monitors with "24" in model
for m in scraper.matcher.monitor_matcher.monitors:
    if 'hp' in m.brand.lower():
        model_lower = m.model.lower()
        # Check if any word in the description matches model parts
        if any(x in text_lower for x in ['24uh', 'hp 24', 'hp24', 'hp monitor']):
            if '24uh' in model_lower or '24' in model_lower:
                print(f"Potential match: ID {m.id}, Brand: {m.brand}, Model: {m.model}, Size: {m.size}")
