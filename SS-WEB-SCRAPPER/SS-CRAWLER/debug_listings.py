# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.scraper.crawler import Crawler
from src.scraper.computer_parser import ComputerListingParser
from src.utils.config import AppConfig

config = AppConfig()
crawler = Crawler(config.scraper)

urls = [
    ("aacph", "https://www.ss.com/msg/lv/electronics/computers/pc/aacph.html"),
    ("dpfex", "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"),
    ("acgdx", "https://www.ss.com/msg/lv/electronics/computers/pc/acgdx.html"),
]

for listing_id, url in urls:
    print(f"\n{'='*70}")
    print(f"Listing: {listing_id}")
    print('='*70)
    
    result = crawler.fetch(url, f"Listing {listing_id}")
    if result.error_type.value == "success":
        parser = ComputerListingParser(result.html, url)
        listing = parser.parse()
        if listing:
            print(f"Title: {listing.title}")
            print(f"Price: {listing.price_eur}")
            print(f"Description:\n{listing.description}")
    else:
        print(f"Error: {result.error_msg}")
