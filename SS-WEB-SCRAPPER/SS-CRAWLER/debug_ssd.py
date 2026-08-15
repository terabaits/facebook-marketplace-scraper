import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper

config = AppConfig.from_yaml()
config.scraper.test_mode = True

scraper = ComputerScraper(config)
scraper.initialize()

print("=== Testing Listing: dpfex.html ===")
url = "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"
listing, match_result = scraper.scrape_single(url)

if listing:
    print(f"\nTitle: {listing.title}")
    
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
        print("\nAdditional SSDs: None")
        print(f"  additional_ssds field: {match_result.additional_ssds}")
else:
    print("Failed to scrape listing")
