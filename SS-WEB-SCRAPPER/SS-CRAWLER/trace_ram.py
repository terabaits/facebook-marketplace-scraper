"""Trace RAM line extraction"""
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
    full_text = f"{listing.title}\n{listing.description}"
    
    print("LINE BY LINE (with RAM keyword matches):")
    print("="*60)
    
    lines = full_text.lower().split('\n')
    ram_keywords = ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas', 'operatīva',
                   'kingston', 'hyperx', 'fury', 'furry', 'corsair', 'gskill', 'crucial', 'adata']
    
    for i, line in enumerate(lines):
        matched = []
        for kw in ram_keywords:
            if kw in line:
                matched.append(kw)
        if matched:
            # Encode to handle unicode
            safe_line = line.encode('utf-8', errors='replace').decode('utf-8')
            print(f"Line {i}: '{safe_line[:80]}...'")
            print(f"  Matched: {matched}")
