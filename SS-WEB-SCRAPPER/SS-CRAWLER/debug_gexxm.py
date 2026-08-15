"""Debug gexxm.html component matching"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator='\n') if desc else ""

print("="*60)
print("FULL LISTING TEXT:")
print("="*60)
print(f"Title: {title}")
print("\nDescription:")
print(description)
print("="*60)

text_lower = (title + " " + description).lower()

# Check what RAM-related text contains
print("\n\nRAM-RELATED SECTIONS:")
ram_keywords = ['ram', 'operativ', 'atmiņ', 'memory', 'ddr']
lines = description.lower().split('\n')
for i, line in enumerate(lines):
    for kw in ram_keywords:
        if kw in line:
            print(f"  Line {i}: {line.strip()}")
            break

# Check what MB-related text contains
print("\n\nMOTHERBOARD-RELATED SECTIONS:")
mb_keywords = ['plate', 'mātesplate', 'motherboard', 'msi', 'tomahawk']
for i, line in enumerate(lines):
    for kw in mb_keywords:
        if kw in line:
            print(f"  Line {i}: {line.strip()}")
            break

# Specific checks
print("\n\nSPECIFIC KEYWORD CHECKS:")
print(f"  'hyperx' in text: {'hyperx' in text_lower}")
print(f"  'fury' in text: {'fury' in text_lower}")
print(f"  'furry' in text: {'furry' in text_lower}")
print(f"  'kingston' in text: {'kingston' in text_lower}")
print(f"  'tomahawk' in text: {'tomahawk' in text_lower}")
print(f"  'max' in text: {'max' in text_lower}")
print(f"  'tomahawk max' in text: {'tomahawk max' in text_lower}")
