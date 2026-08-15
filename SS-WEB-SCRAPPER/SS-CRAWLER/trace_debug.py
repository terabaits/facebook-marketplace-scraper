"""Standalone test to trace matching"""
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
normalized = normalize_text(full_text)

print("="*60)
print("STEP 1: Extract RAM line from text")
print("="*60)

lines = full_text.lower().split('\n')
ram_line = ""
for line in lines:
    if any(kw in line for kw in ['ram', 'operativ', 'atmiņ']):
        ram_line = line
        break

print(f"RAM line found: '{ram_line}'")
print(f"'furry' in ram_line: {'furry' in ram_line}")
print(f"'hyperx' in ram_line: {'hyperx' in ram_line}")

print("\n" + "="*60)
print("STEP 2: Check RAM matching logic")
print("="*60)

# Init scraper
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Find RAM 918
for ram in scraper.matcher.ram_matcher.rams:
    if ram.id == 918:
        print(f"\nRAM ID 918: {ram.name}")
        ram_name_lower = ram.name.lower()
        
        # Check compound models
        compound_models = {
            'viper': 'patriot',
            'trident': 'gskill',
            'ripjaws': 'gskill',
            'vengeance': 'corsair',
            'dominator': 'corsair',
            'ballistix': 'crucial',
            'fury': 'kingston',
        }
        
        compound_model_matched = False
        for model_keyword, implied_brand in compound_models.items():
            if model_keyword in ram_name_lower and model_keyword in ram_line:
                print(f"  Compound model check: '{model_keyword}' in both name and line")
                if 'steel' in ram_name_lower and 'steel' in ram_line and model_keyword == 'viper':
                    compound_model_matched = True
                    print("    -> Viper Steel match!")
                elif 'z' in ram_name_lower and 'z' in ram_line and model_keyword in ('trident', 'vengeance'):
                    compound_model_matched = True
                    print("    -> Trident Z / Vengeance Z match!")
        
        print(f"  compound_model_matched={compound_model_matched}")
        
        # Check model keywords
        model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                          'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                          't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                          'viper', 'steel', 'patriot', 'hyperx', 'aegis',
                          'vipersteel', 'viper steel']
        has_model_in_text = compound_model_matched
        print(f"\n  Checking model keywords (has_model_in_text={has_model_in_text}):")
        for kw in model_keywords:
            if kw in ram_name_lower:
                in_line = kw in ram_line
                print(f"    '{kw}' in ram_line: {in_line}")
                if in_line:
                    has_model_in_text = True
        
        print(f"\n  After keyword loop: has_model_in_text={has_model_in_text}")
        
        # Furry typo check
        if not has_model_in_text and 'fury' in ram_name_lower and 'furry' in ram_line:
            print(f"  -> FURRY TYPO DETECTED! 'fury' in name, 'furry' in text")
            has_model_in_text = True
        
        print(f"\n  FINAL: has_model_in_text={has_model_in_text}")
        
        # Check brand
        brand = 'kingston'
        has_brand = brand in ram_line
        print(f"\n  Brand check: '{brand}' in ram_line: {has_brand}")
        
        if not has_brand and 'hyperx' in ram_name_lower and 'hyperx' in ram_line:
            has_brand = True
            print("  -> HyperX in text, treating as Kingston brand")
        
        print(f"  FINAL has_brand={has_brand}")
        print(f"\n  is_specific_ram would be: has_brand={has_brand} AND has_model_in_text={has_model_in_text}")
        break

print("\n" + "="*60)
print("STEP 3: Check Motherboard matching")
print("="*60)

# Get MB line
mb_line = ""
for line in lines:
    if any(kw in line for kw in ['plate', 'mātesplate', 'mb:', 'motherboard']):
        mb_line = line
        break

print(f"MB line found: '{mb_line}'")
print(f"'gaming' in MB line: {'gaming' in mb_line}")
print(f"'plus' in MB line: {'plus' in mb_line}")
print(f"'max' in MB line: {'max' in mb_line}")
print(f"'tomahawk' in MB line: {'tomahawk' in mb_line}")

# Check what gets matched
for mb in scraper.matcher.motherboard_matcher.motherboards:
    if mb.id in [7165, 7203]:
        model_lower = mb.model.lower()
        print(f"\nMB ID {mb.id}: {mb.model}")
        print(f"  'gaming plus max' in model: {'gaming plus max' in model_lower}")
        print(f"  'tomahawk' in model: {'tomahawk' in model_lower}")
        print(f"  'gaming' in model: {'gaming' in model_lower}")
        print(f"  'plus' in model: {'plus' in model_lower}")
        print(f"  'max' in model: {'max' in model_lower}")
