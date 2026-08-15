"""Test multi-SSD and monitor detection for listing dpfex.html"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper
from src.scraper.computer_matcher import ComputerMatcher

config = AppConfig.from_yaml()
config.scraper.test_mode = True

scraper = ComputerScraper(config)
scraper.initialize()

# Check for HP 24" monitor in database
print("=== HP 24\" Monitors in Database ===")
for m in scraper.matcher.monitor_matcher.monitors:
    try:
        size = float(m.size) if m.size else 0
        if 'hp' in m.brand.lower() and size and abs(size - 24) < 1:
            print(f"ID: {m.id}, Brand: {m.brand}, Model: {m.model}, Size: {m.size}\"")
    except (ValueError, TypeError):
        pass

print("\n=== Testing Listing: dpfex.html ===")
url = "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"
listing, match_result = scraper.scrape_single(url)

if listing:
    print(f"\nTitle: {listing.title}")
    print(f"Description: {listing.description[:200]}...")
    
    print("\n=== SSD Detection ===")
    if match_result.ssd:
        ssd = match_result.ssd
        if isinstance(ssd, dict):
            print(f"Primary SSD: {ssd.get('brand', 'Unknown')} {ssd.get('model', 'Unknown')} (ID: {ssd.get('id', 'N/A')})")
        else:
            print(f"Primary SSD: {ssd.brand} {ssd.model} (ID: {ssd.id})")
    else:
        print("Primary SSD: Not detected")
    
    if match_result.additional_ssds:
        print(f"\nAdditional SSDs: {len(match_result.additional_ssds)}")
        for i, ssd in enumerate(match_result.additional_ssds, 1):
            print(f"  SSD {i+1}: {ssd.get('brand', 'Generic')} {ssd.get('capacity_gb')}GB")
    else:
        print("Additional SSDs: None")
    
    print("\n=== Monitor Detection ===")
    if match_result.monitor:
        mon = match_result.monitor
        if isinstance(mon, dict):
            print(f"Monitor: {mon.get('brand', 'Unknown')} {mon.get('model', 'Unknown')}")
            print(f"Size: {mon.get('size', 'N/A')}\"")
            print(f"ID: {mon.get('id', 'N/A')}")
        else:
            print(f"Monitor: {mon.brand} {mon.model}")
            print(f"Size: {mon.size}\"")
            print(f"ID: {mon.id}")
    else:
        print("Monitor: Not detected")
        print(f"Monitor Confidence: {match_result.monitor_confidence}")
        print(f"Monitor Method: {match_result.monitor_method}")
else:
    print("Failed to scrape listing")
