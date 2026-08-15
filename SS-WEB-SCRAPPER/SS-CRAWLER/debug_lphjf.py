#!/usr/bin/env python3
"""Debug the actual lphjf listing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import requests
from bs4 import BeautifulSoup
from src.utils.text import normalize_text

# Fetch actual listing
url = "https://www.ss.com/msg/lv/electronics/computers/pc/lphjf.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')
msg_body = soup.find('div', class_='msg_body')
if msg_body:
    text = msg_body.get_text(separator='\n', strip=True)
else:
    text = soup.get_text(separator='\n', strip=True)

print("="*60)
print("ACTUAL LPHJF LISTING TEXT")
print("="*60)
print(text)

print("\n" + "="*60)
print("NORMALIZED")
print("="*60)
normalized = normalize_text(text)
print(normalized)

print("\n" + "="*60)
print("SSD-RELATED SEGMENTS")
print("="*60)
for line in text.split('\n'):
    if 'ssd' in line.lower() or 'kingston' in line.lower() or 'nv2' in line.lower() or 'tb' in line.lower():
        print(f"  {line}")
