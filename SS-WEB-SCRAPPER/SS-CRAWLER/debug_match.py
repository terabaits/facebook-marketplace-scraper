"""Debug matching for gexxm.html"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from bs4 import BeautifulSoup
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper

# Fetch the listing
url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator=' ') if desc else ""

print("LISTING TEXT:")
print("="*60)
print(f"Title: {title}")
print(f"\nDescription (first 500 chars):")
print(description[:500])
print("="*60)

# Initialize scraper
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

full_text = f"{title} {description}".lower()
print("\n\nCHECKING FOR COMPONENTS IN TEXT:")
print("="*60)

# Check RAM patterns
print("\nRAM CHECK:")
print(f"  'hyperx' in text: {'hyperx' in full_text}")
print(f"  'fury' in text: {'fury' in full_text}")
print(f"  'kingston' in text: {'kingston' in full_text}")

# Check what RAMs are searched
print("\n  Looking for RAM ID 918 in database...")
for ram in scraper.matcher.ram_matcher.rams:
    if ram.id == 918:
        print(f"  Found ID 918: {ram.name}")
        print(f"    normalized_name: {ram.normalized_name}")
        # Check if name parts are in text
        print(f"    'hyperx' in text: {'hyperx' in full_text}")
        print(f"    'fury' in text: {'fury' in full_text}")
        break

# Check MB patterns
print("\n\nMOTHERBOARD CHECK:")
print(f"  'msi' in text: {'msi' in full_text}")
print(f"  'b450' in text: {'b450' in full_text}")
print(f"  'tomahawk' in text: {'tomahawk' in full_text}")
print(f"  'max' in text: {'max' in full_text}")

print("\n  Looking for MB ID 7203 (MSI B450 TOMAHAWK MAX)...")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id == 7203:
        print(f"  Found ID 7203: {mb.brand} {mb.model}")
        print(f"    Socket: {mb.socket}, Chipset: {mb.chipset}")
        # Check if in text
        brand_model = f"{mb.brand} {mb.model}".lower()
        print(f"    Brand+Model pattern in text: {brand_model.replace(' ', '') in full_text.replace(' ', '')}")
        break

print("\n  Looking for MB ID 7165 (what was matched)...")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id == 7165:
        print(f"  Found ID 7165: {mb.brand} {mb.model}")
        print(f"    Socket: {mb.socket}, Chipset: {mb.chipset}")
        break

# Run the match
print("\n\nRUNNING MATCH:")
print("="*60)
match_result = scraper.matcher.match(title, description, 500.0)

print(f"\nRAM matched: {match_result.ram}")
print(f"  Confidence: {match_result.ram_confidence}")
print(f"  Method: {match_result.ram_method}")

print(f"\nMotherboard matched: {match_result.motherboard}")
print(f"  Confidence: {match_result.motherboard_confidence}")
print(f"  Method: {match_result.motherboard_method}")
