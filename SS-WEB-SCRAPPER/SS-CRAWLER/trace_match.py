"""Trace the actual matching logic"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from bs4 import BeautifulSoup
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper
from src.utils.text import normalize_text
import re

# Fetch
url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator='\n') if desc else ""

full_text = f"{title}\n{description}"
print("FULL TEXT (first 2000 chars):")
print(full_text[:2000])

# Get normalized
normalized = normalize_text(full_text)
print("\n\nNORMALIZED TEXT (first 1000 chars):")
print(normalized[:1000])

# Check patterns
print("\n\nPATTERN CHECKS IN NORMALIZED TEXT:")
print(f"'furry': {'furry' in normalized}")
print(f"'fury': {'fury' in normalized}")
print(f"'hyperx': {'hyperx' in normalized}")
print(f"'gaming plus max': {'gaming plus max' in normalized}")
print(f"'gaming': {'gaming' in normalized}")
print(f"'plus': {'plus' in normalized}")
print(f"'max': {'max' in normalized}")
print(f"'tomahawk': {'tomahawk' in normalized}")

# Init scraper
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

print("\n\n" + "="*60)
print("CHECKING RAM ID 918 MATCH")
print("="*60)

# Find RAM 918
for ram in scraper.matcher.ram_matcher.rams:
    if ram.id == 918:
        print(f"RAM 918: {ram.name}")
        ram_name = normalize_text(ram.name)
        print(f"Normalized name: {ram_name}")
        
        # Simulate the matching logic
        print("\nSimulating match logic:")
        
        # Check fuzzy score
        from rapidfuzz import fuzz
        score = fuzz.token_set_ratio(normalized, ram_name)
        print(f"  Fuzzy score: {score}")
        
        # Check if in normalized
        if ram_name in normalized:
            print(f"  EXACT MATCH: '{ram_name}' in normalized")
        else:
            print(f"  No exact match for '{ram_name}'")
        
        # Check model parts
        model_parts = ram.name.lower().split()
        print(f"  Model parts: {model_parts}")
        for part in model_parts:
            if len(part) >= 3:
                if part in normalized:
                    print(f"    '{part}' found in normalized")
                elif part == 'fury' and 'furry' in normalized:
                    print(f"    'fury' -> 'furry' typo detected!")
        break

print("\n\n" + "="*60)
print("CHECKING MB IDs")
print("="*60)

for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id in [7165, 7203]:
        mb_name = normalize_text(f"{mb.brand} {mb.model}")
        print(f"\nMB {mb.id}: {mb.brand} {mb.model}")
        print(f"  Normalized: {mb_name}")
        print(f"  In normalized text: {mb_name in normalized}")
        
        # Check parts
        parts = mb.model.lower().split()
        for part in parts:
            if part in normalized:
                print(f"    '{part}' found")
