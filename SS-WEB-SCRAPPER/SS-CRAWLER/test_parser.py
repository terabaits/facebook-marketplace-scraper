"""Test what the parser extracts"""
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
    
    desc_lower = listing.description.lower()
    print("\nCHECKS:")
    print(f"'kingston' in desc: {'kingston' in desc_lower}")
    print(f"'furry' in desc: {'furry' in desc_lower}")
    print(f"'fury' in desc: {'fury' in desc_lower}")
    print(f"'hyperx' in desc: {'hyperx' in desc_lower}")
    print(f"'msi' in desc: {'msi' in desc_lower}")
    print(f"'gaming' in desc: {'gaming' in desc_lower}")
    print(f"'tomahawk' in desc: {'tomahawk' in desc_lower}")
    print(f"'plus' in desc: {'plus' in desc_lower}")
    print(f"'max' in desc: {'max' in desc_lower}")
else:
    print("Parser returned None!")
