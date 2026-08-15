#!/usr/bin/env python3
"""Fetch actual listing text for fcddo."""

import sys
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/fcddo.html"
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

# Get title
title = soup.find('h2', {'class': 'headtitle'})
if title:
    sys.stdout.buffer.write(b"Title: ")
    sys.stdout.buffer.write(title.text.strip().encode('utf-8'))
    sys.stdout.buffer.write(b"\n")

# Get description
desc_div = soup.find('div', {'id': 'msg_div_msg'})
if desc_div:
    sys.stdout.buffer.write(b"\nDescription:\n")
    sys.stdout.buffer.write(desc_div.text.strip().encode('utf-8'))
    sys.stdout.buffer.write(b"\n")

# Write to file
with open('fcddo_content.txt', 'w', encoding='utf-8') as f:
    f.write("Title:\n")
    if title:
        f.write(title.text.strip())
        f.write("\n\n")
    
    f.write("Description:\n")
    if desc_div:
        f.write(desc_div.text.strip())
        f.write("\n\n")
    
    f.write("="*80)
    f.write("\nAll text:\n")
    f.write("="*80)
    f.write("\n")
    text = soup.get_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        f.write(line)
        f.write("\n")

sys.stdout.buffer.write(b"\nContent saved to fcddo_content.txt\n")
