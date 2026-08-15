"""Trace through the matching to see what's happening"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from bs4 import BeautifulSoup
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper
from src.utils.text import normalize_text

# Fetch the listing
url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator=' ') if desc else ""

full_text = f"{title} {description}".lower()
print("TEXT LOWER:")
print(full_text[:1000])

# Initialize
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Debug RAM matching
print("\n\n" + "="*60)
print("RAM MATCHING DEBUG")
print("="*60)

# Get RAM line
lines = full_text.split('\n')
ram_line = ""
for line in lines:
    if any(kw in line for kw in ['ram', 'operativ', 'atmiņ']):
        ram_line = line
        break

print(f"RAM line: {ram_line}")
print(f"'furry' in ram_line: {'furry' in ram_line}")
print(f"'fury' in ram_line: {'fury' in ram_line}")
print(f"'hyperx' in ram_line: {'hyperx' in ram_line}")

# Check RAM 918
print("\nChecking RAM ID 918:")
for ram in scraper.matcher.ram_matcher.rams:
    if ram.id == 918:
        print(f"  Name: {ram.name}")
        print(f"  Normalized: {normalize_text(ram.name)}")
        
        # Check what the matcher would see
        name_lower = ram.name.lower()
        print(f"  'fury' in name: {'fury' in name_lower}")
        print(f"  'hyperx' in name: {'hyperx' in name_lower}")
        
        # Check if furry would match
        if 'fury' in name_lower:
            print(f"  Would 'furry' match 'fury'? {'furry' in ram_line and 'fury' in name_lower}")
        break

# Debug MB matching
print("\n\n" + "="*60)
print("MOTHERBOARD MATCHING DEBUG")
print("="*60)

# Get MB line
mb_line = ""
for line in lines:
    if any(kw in line.lower() for kw in ['plate', 'mātesplate', 'msi', 'b450']):
        mb_line = line
        break

print(f"MB line: {mb_line}")
print(f"'gaming plus' in text: {'gaming plus' in full_text}")
print(f"'tomahawk' in text: {'tomahawk' in full_text}")

# Check MB 7165 (TOMAHAWK) vs 7203 (GAMING PLUS MAX)
print("\nChecking MB ID 7165 (TOMAHAWK):")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id == 7165:
        print(f"  {mb.brand} {mb.model}")
        model_lower = mb.model.lower()
        print(f"  'tomahawk' in model: {'tomahawk' in model_lower}")
        print(f"  'gaming' in model: {'gaming' in model_lower}")
        break

print("\nChecking MB ID 7203 (GAMING PLUS MAX):")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id == 7203:
        print(f"  {mb.brand} {mb.model}")
        model_lower = mb.model.lower()
        print(f"  'gaming' in model: {'gaming' in model_lower}")
        print(f"  'plus' in model: {'plus' in model_lower}")
        print(f"  'max' in model: {'max' in model_lower}")
        break

# Run actual match
print("\n\n" + "="*60)
print("RUNNING ACTUAL MATCH")
print("="*60)

match_result = scraper.matcher.match(title, description, 500.0)

print(f"\nRAM result: {match_result.ram}")
if match_result.ram:
    if isinstance(match_result.ram, dict):
        print(f"  ID: {match_result.ram.get('id')}")
        print(f"  Name: {match_result.ram.get('name')}")
    else:
        print(f"  ID: {match_result.ram.id}")
        print(f"  Name: {match_result.ram.name}")
print(f"  Confidence: {match_result.ram_confidence}")
print(f"  Method: {match_result.ram_method}")

print(f"\nMB result: {match_result.motherboard}")
if match_result.motherboard:
    if isinstance(match_result.motherboard, dict):
        print(f"  ID: {match_result.motherboard.get('id')}")
        print(f"  Name: {match_result.motherboard.get('brand')} {match_result.motherboard.get('model')}")
    else:
        print(f"  ID: {match_result.motherboard.id}")
        print(f"  Name: {match_result.motherboard.brand} {match_result.motherboard.model}")
print(f"  Confidence: {match_result.motherboard_confidence}")
print(f"  Method: {match_result.motherboard_method}")
