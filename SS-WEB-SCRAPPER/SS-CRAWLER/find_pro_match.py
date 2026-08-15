#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/game-consoles/hmpoc.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract title
title_elem = soup.find('title')
title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""

# Extract description
msg_div = soup.find('div', {'id': 'msg_div_msg'})
description = ""
if msg_div:
    description = msg_div.get_text(separator=' ', strip=True)

full_text = f"{title} {description}".strip()
text_lower = full_text.lower()

print("Searching for 'pro' pattern matches...")
print()

# Check each word
print("All words:")
for i, word in enumerate(text_lower.split()):
    print(f"  {i}: '{word}'")
    
print()
print("Words containing 'pro':")
for word in text_lower.split():
    if 'pro' in word:
        print(f"  '{word}' at positions: {[i for i in range(len(word)-2) if word[i:i+3] == 'pro']}")
