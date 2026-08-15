# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.scraper.computer_scraper import ComputerScraper
from src.utils.config import AppConfig

config = AppConfig()
scraper = ComputerScraper(config)

# Test the full computer scraper
url = "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"
print("Testing computer scraper...")
scraper.initialize()

listing, match_result = scraper.scrape_single(url)

print("\nResults:")
print(f"  Listing ID: {listing.listing_id if listing else 'None'}")
print(f"  Match result type: {type(match_result)}")

if match_result:
    print(f"\n  Monitor: {match_result.monitor}")
    print(f"  Monitor confidence: {match_result.monitor_confidence}")
    print(f"  Monitor method: {match_result.monitor_method}")
    print(f"  Has monitor: {match_result.has_monitor}")
