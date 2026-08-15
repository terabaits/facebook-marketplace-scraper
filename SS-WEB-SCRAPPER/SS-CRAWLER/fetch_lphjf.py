#!/usr/bin/env python3
"""Fetch actual lphjf listing text."""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/lphjf.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')
msg_body = soup.find('div', class_='msg_body')
if msg_body:
    text = msg_body.get_text(separator='\n', strip=True)
else:
    text = soup.get_text(separator='\n', strip=True)

# Save to file
with open('lphjf_actual.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print("Listing text saved to lphjf_actual.txt")
print("\nFirst 2000 characters:")
print(text[:2000])
