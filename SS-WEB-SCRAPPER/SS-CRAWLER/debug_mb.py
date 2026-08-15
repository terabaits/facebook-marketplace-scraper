"""Debug gexxm motherboard matching"""
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

desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator='\n') if desc else ""

print("FULL DESCRIPTION:")
print("="*60)
print(description)
print("="*60)

text_lower = description.lower()

# Check what MB-related text contains
print("\n\nMOTHERBOARD-RELATED SECTIONS:")
mb_keywords = ['plate', 'mātesplate', 'motherboard', 'msi', 'gaming', 'plus', 'max', 'b450']
lines = description.lower().split('\n')
for i, line in enumerate(lines):
    for kw in mb_keywords:
        if kw in line:
            print(f"  Line {i}: {line.strip()}")
            break

# Initialize scraper to check database
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Find MSI B450 GAMING PLUS MAX
print("\n\nLooking for MSI B450 GAMING PLUS MAX in database:")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if 'gaming' in mb.model.lower() and 'plus' in mb.model.lower() and 'b450' in mb.chipset.lower():
        print(f"  ID {mb.id}: {mb.brand} {mb.model}")
        print(f"    Socket: {mb.socket}, Chipset: {mb.chipset}")

print("\n\nWhat was matched (ID 7165):")
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id == 7165:
        print(f"  ID {mb.id}: {mb.brand} {mb.model}")
        print(f"    Socket: {mb.socket}, Chipset: {mb.chipset}")
