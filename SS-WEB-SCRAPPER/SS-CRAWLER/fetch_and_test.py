# -*- coding: utf-8 -*-
"""Test the full computer matcher with the actual SS.com listing."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER\\src')

import requests
import re
from bs4 import BeautifulSoup

def normalize_text(text):
    """Normalize text for search matching."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Fetch the actual listing
url = "https://www.ss.com/msg/lv/electronics/computers/pc/alnnx.html"
print(f"Fetching: {url}")
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(response.content, 'html.parser')

# Extract title
title_elem = soup.select_one('h2')
title = title_elem.get_text(strip=True) if title_elem else "Unknown"
print(f"Title: {title}")

# Extract description (similar to computer_parser._extract_description)
desc_elem = soup.select_one('#msg_div_msg')
text_parts = []
for child in desc_elem.children:
    if child.name == 'div' and 'float' in child.get('style', ''):
        continue
    if child.name == 'table':
        if child.find('img'):
            continue
        if 'options_list' in child.get('class', []):
            rows = child.find_all('tr')
            option_lines = []
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 2:
                    label_text = tds[0].get_text(strip=True).lower()
                    value_text = tds[1].get_text(strip=True)
                    if value_text:
                        full_text = f"{label_text}: {value_text}"
                        option_lines.append(full_text)
            for line in option_lines:
                text_parts.append(line)
            continue
    text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
    if text:
        text_parts.append(text)

description = '\n'.join(text_parts) if text_parts else ""

print(f"\nDescription:")
print(description)

full_text = f"{title} {description}".strip()
normalized = normalize_text(full_text)

print(f"\n=== Normalized Text ===")
print(f"{normalized}")

print(f"\n=== Key Terms Check ===")
print(f"'hyperx' in text: {'hyperx' in normalized}")
print(f"'fury' in text: {'fury' in normalized}")
print(f"'kingston' in text: {'kingston' in normalized}")
print(f"'asus' in text: {'asus' in normalized}")
print(f"'tuf' in text: {'tuf' in normalized}")
print(f"'b450plus' in text: {'b450plus' in normalized}")
print(f"'b450-plus' in text: {'b450-plus' in normalized}")
print(f"'asus tuf b450plus gaming' in text: {'asus tuf b450plus gaming' in normalized}")

# Check the RAM ID 3289
print(f"\n=== Expected Results ===")
print(f"RAM should match ID 3289: Kingston HyperX 16 GB DDR4-4800")
print(f"Motherboard should match ID 7446: Asus TUF B450-PLUS GAMING")

print(f"\n=== Test Complete ===")
print("Run 'python main.py test-url \"https://www.ss.com/msg/lv/electronics/computers/pc/alnnx.html\" --computers' to verify")
