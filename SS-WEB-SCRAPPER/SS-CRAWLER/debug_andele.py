#!/usr/bin/env python3
"""Debug script to inspect Andele category page HTML."""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER')

import requests
from bs4 import BeautifulSoup
import re

url = "https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:409"

print(f"Fetching: {url}")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")

# Save HTML
with open('andele_gpu_category_debug.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("Saved to: andele_gpu_category_debug.html")

# Parse and analyze
soup = BeautifulSoup(response.text, 'html.parser')

# Find all listing links
listing_links = soup.find_all('a', href=re.compile(r'/perle/\d+/'))
print(f"\nFound {len(listing_links)} total links matching pattern")

# Extract unique IDs
seen_ids = set()
unique_urls = []
for link in listing_links:
    href = link.get('href', '')
    match = re.search(r'/perle/(\d+)/', href)
    if match:
        listing_id = match.group(1)
        if listing_id not in seen_ids:
            seen_ids.add(listing_id)
            unique_urls.append((listing_id, href))

print(f"Unique listing IDs: {len(unique_urls)}")
print("\nFirst 10 listings:")
for i, (lid, url) in enumerate(unique_urls[:10]):
    print(f"  {i+1}. ID {lid}: {url[:80]}...")

# Look for different containers
print("\n\nLooking for listing containers...")

# Try different selectors
selectors = [
    'a[href*="/perle/"]',
    '.product-item a',
    '.listing-item a',
    '.item a',
    '[class*="product"] a[href*="/perle/"]',
    '[class*="listing"] a[href*="/perle/"]',
    '.grid a[href*="/perle/"]',
]

for selector in selectors:
    elems = soup.select(selector)
    print(f"  Selector '{selector}': {len(elems)} matches")
