#!/usr/bin/env python3
"""Debug component matching for a specific listing."""
import sys
sys.path.insert(0, 'src')

from src.scraper.crawler import Crawler
from src.utils.config import AppConfig
from pathlib import Path

def main():
    config = AppConfig.from_yaml('config.yaml')
    crawler = Crawler(config.scraper)
    
    url = "https://www.ss.com/msg/lv/electronics/computers/pc/bghgpe.html"
    result = crawler.fetch(url)
    
    if result.html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(result.html, 'html.parser')
        desc = soup.select_one('#msg_div_msg')
        title_elem = soup.select_one('h2')
        
        title = title_elem.get_text(strip=True) if title_elem else ""
        description = desc.get_text(separator=' ', strip=True) if desc else ""
        
        full_text = f"{title} {description}"
        
        print("=" * 70)
        print("FULL LISTING TEXT:")
        print("=" * 70)
        print(full_text)
        print()
        
        # Test RAM extraction
        print("=" * 70)
        print("RAM DEBUG:")
        print("=" * 70)
        
        from src.utils.text import normalize_text
        normalized = normalize_text(full_text)
        print(f"Normalized text: {normalized[:500]}")
        print()
        
        # Check for RAM patterns
        import re
        ram_patterns = [
            r'\d+\s*gb\s*ram',
            r'\d+\s*gb\s*ddr',
            r'ram\s*\d+',
            r'ddr\d',
            r'16\s*gb',
            r'32\s*gb',
        ]
        
        print("RAM pattern matches:")
        for pattern in ram_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            if matches:
                print(f"  Pattern '{pattern}': {matches}")
        
        # Check specific text around RAM mentions
        if 'ram' in normalized:
            pos = normalized.find('ram')
            start = max(0, pos - 50)
            end = min(len(normalized), pos + 100)
            print(f"\nText around 'ram':")
            print(f"  ...{normalized[start:end]}...")
        
        if '16' in normalized:
            pos = normalized.find('16')
            start = max(0, pos - 30)
            end = min(len(normalized), pos + 50)
            print(f"\nText around '16':")
            print(f"  ...{normalized[start:end]}...")
        
        # Test SSD extraction
        print()
        print("=" * 70)
        print("SSD DEBUG:")
        print("=" * 70)
        
        ssd_patterns = [
            r'\d+\s*gb\s*ssd',
            r'\d+\s*tb\s*ssd',
            r'ssd\s*\d+',
            r'nvme',
            r'm\.2',
            r'250\s*gb',
            r'256\s*gb',
        ]
        
        print("SSD pattern matches:")
        for pattern in ssd_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            if matches:
                print(f"  Pattern '{pattern}': {matches}")
        
        # Check for Intel mentions
        if 'intel' in normalized:
            print(f"\n'Intel' found in text")
            positions = [m.start() for m in re.finditer('intel', normalized)]
            for pos in positions:
                start = max(0, pos - 30)
                end = min(len(normalized), pos + 30)
                print(f"  Context: ...{normalized[start:end]}...")
        
        # Check generic SSD mentions
        generic_patterns = [r'generic', r'sata', r'hdd', r'cietais']
        print("\nGeneric/storage mentions:")
        for pattern in generic_patterns:
            if pattern in normalized:
                print(f"  Found: {pattern}")

if __name__ == "__main__":
    main()
