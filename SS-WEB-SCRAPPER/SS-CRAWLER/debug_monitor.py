"""Debug monitor matching for pbdhn.html"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from bs4 import BeautifulSoup
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper

# Fetch the listing
url = "https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator=' ') if desc else ""

print("LISTING TEXT:")
print("="*60)
print(f"Title: {title}")
print(f"Description: {description[:500]}...")
print()

# Check for monitor model patterns
text_lower = (title + " " + description).lower()
print("CHECKING FOR MONITOR MODELS:")
print("="*60)

# Check for LG models
lg_patterns = ['lg', '24gn', 'gn600', 'ultragear', '24gn600']
for pattern in lg_patterns:
    if pattern in text_lower:
        print(f"  Found: '{pattern}'")
        # Show context
        idx = text_lower.find(pattern)
        start = max(0, idx - 30)
        end = min(len(text_lower), idx + len(pattern) + 30)
        print(f"    Context: ...{text_lower[start:end]}...")

# Now run the matcher
print("\n" + "="*60)
print("RUNNING MATCHER:")
print("="*60)

config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Find the specific monitor
print("\nLooking for monitor ID 29860 (LG 24GN600-B):")
for mon in scraper.matcher.monitor_matcher.monitors:
    if mon.id == 29860:
        print(f"  Found: {mon.brand} {mon.model}")
        print(f"  Size: {mon.size}")
        print(f"  Resolution: {mon.resolution}")
        print(f"  Refresh: {mon.refresh_rate}")
        print(f"  Keywords: {mon.search_keywords}")
        break

# Check if model pattern exists in text
model_variants = ['24gn600', '24gn600-b', 'gn600', 'gn600-b']
print("\nChecking model variants in text:")
for variant in model_variants:
    if variant in text_lower:
        print(f"  Found variant: '{variant}'")
