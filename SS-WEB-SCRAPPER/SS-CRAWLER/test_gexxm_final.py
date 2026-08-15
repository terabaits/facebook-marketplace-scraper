"""Final test for gexxm"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper

# Fetch
url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

# Init scraper
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Get parsed data
from src.scraper.computer_parser import ComputerListingParser
parser = ComputerListingParser(resp.text, url)
listing = parser.parse()

if listing:
    print("TITLE:", listing.title)
    print("\nDESCRIPTION:")
    print(listing.description[:500])
    
    # Run match
    match_result = scraper.matcher.match(listing.title, listing.description, 500.0)
    
    print("\n" + "="*60)
    print("MATCH RESULTS:")
    print("="*60)
    
    print(f"\nRAM:")
    if match_result.ram:
        print(f"  Name: {match_result.ram.get('name') if isinstance(match_result.ram, dict) else match_result.ram.name}")
        print(f"  ID: {match_result.ram.get('id') if isinstance(match_result.ram, dict) else match_result.ram.id}")
    else:
        print("  None (fallback)")
    print(f"  Confidence: {match_result.ram_confidence}")
    print(f"  Method: {match_result.ram_method}")
    
    print(f"\nMotherboard:")
    if match_result.motherboard:
        print(f"  Name: {match_result.motherboard.get('brand', '')} {match_result.motherboard.get('model', '') if isinstance(match_result.motherboard, dict) else match_result.motherboard.model}")
        print(f"  ID: {match_result.motherboard.get('id') if isinstance(match_result.motherboard, dict) else match_result.motherboard.id}")
    print(f"  Confidence: {match_result.motherboard_confidence}")
    print(f"  Method: {match_result.motherboard_method}")
