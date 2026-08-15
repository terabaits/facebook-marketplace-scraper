"""Test what the parser extracts now"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from src.scraper.computer_parser import ComputerListingParser

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

parser = ComputerListingParser(resp.text, url)
listing = parser.parse()

if listing:
    print("TITLE:")
    print(listing.title)
    print("\n" + "="*60)
    print("DESCRIPTION:")
    print("="*60)
    print(listing.description)
    print("="*60)
else:
    print("Parser returned None!")
