#!/usr/bin/env python3
"""Fetch and show the actual listing description from ss.com."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import requests
from bs4 import BeautifulSoup
from src.utils.text import normalize_text


def fetch_listing(url):
    """Fetch listing and extract description."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try to find the description
    # Look for the message body
    msg_body = soup.find('div', class_='msg_body')
    if msg_body:
        text = msg_body.get_text(separator='\n', strip=True)
    else:
        # Alternative: look for any large text block
        text = soup.get_text(separator='\n', strip=True)
    
    return text


def extract_ssd_mentions(text):
    """Extract SSD mentions from text."""
    normalized = normalize_text(text)
    
    # Look for SSD patterns
    ssd_patterns = [
        r'(samsung|kingston|crucial|wd|western digital)\s+(\w+[\s\w]*)\s+(\d+)\s*gb',
        r'(\d+)\s*gb\s+(ssd|nvme|m\.2)',
    ]
    
    found = []
    for pattern in ssd_patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            found.append(match.group(0))
    
    return found


if __name__ == "__main__":
    import re
    
    url = "https://www.ss.com/msg/lv/electronics/computers/pc/londo.html"
    text = fetch_listing(url)
    
    print("=" * 60)
    print("EXTRACTED TEXT:")
    print("=" * 60)
    safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
    print(safe_text[:2000])
    
    print("\n" + "=" * 60)
    print("LOOKING FOR SSD MENTIONS:")
    print("=" * 60)
    ssds = extract_ssd_mentions(text)
    for ssd in ssds:
        print(f"  Found: {ssd}")
    
    print("\n" + "=" * 60)
    print("LOOKING FOR PSU MENTIONS:")
    print("=" * 60)
    # Look for PSU patterns
    psu_patterns = [
        r'(cooler master|be quiet|corsair|evga|seasonic|thermaltake|msi).*?(\d{3,4})\s*w',
        r'(\d{3,4})\s*w.*?(psu|power supply|barosanas bloks)',
    ]
    for pattern in psu_patterns:
        for match in re.finditer(pattern, normalize_text(text), re.IGNORECASE):
            print(f"  Found: {match.group(0)}")
