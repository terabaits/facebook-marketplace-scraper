"""Check the listing pbdhn.html content"""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html"
headers = {'User-Agent': 'Mozilla/5.0'}

resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

# Get title
title = soup.find('h1')
if title:
    print(f"TITLE: {title.get_text(strip=True)}")

# Get description
desc = soup.find('div', id='msg_div_msg')
if desc:
    text = desc.get_text(separator='\n')
    print(f"\nDESCRIPTION:")
    print(text)
    print(f"\nLOWERCASE:")
    print(text.lower())
    
    # Check for monitor keywords
    text_lower = text.lower()
    monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays', 'screen']
    found_keywords = [kw for kw in monitor_keywords if kw in text_lower]
    print(f"\nMonitor keywords found: {found_keywords}")
    
    # Check for GPU patterns that might cause false matches
    gpu_patterns = ['rx 570', 'rx 580', 'gtx', 'rtx', 'radeon', 'geforce']
    found_gpus = [p for p in gpu_patterns if p in text_lower]
    print(f"GPU patterns found: {found_gpus}")
