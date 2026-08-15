#!/usr/bin/env python3
"""Debug PSU matching for a specific listing."""

import sys
sys.path.insert(0, 'src')

from src.database.connection import init_database, get_session
from src.database.repository import PSURepository
from src.scraper.psu_matcher import PSUMatcher
from src.scraper.crawler import Crawler
from src.utils.config import AppConfig
from pathlib import Path

def main():
    # Initialize
    config = AppConfig.from_yaml('config.yaml')
    init_database(config.database)
    
    # Fetch the listing
    crawler = Crawler(config.scraper)
    result = crawler.fetch('https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html')
    
    if not result.html:
        print("Failed to fetch listing")
        return
    
    # Parse description
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(result.html, 'html.parser')
    desc = soup.select_one('#msg_div_msg')
    title_elem = soup.select_one('h2')
    
    title = title_elem.get_text(strip=True) if title_elem else ""
    description = desc.get_text(separator=' ', strip=True) if desc else ""
    
    full_text = f"{title} {description}"
    
    print("=" * 70)
    print("LISTING TEXT:")
    print("=" * 70)
    print(full_text[:1500])
    print()
    
    # Load PSUs and match
    with get_session() as session:
        from sqlalchemy import text
        psus = session.execute(text("SELECT * FROM psu_reference")).fetchall()
        
        # Convert to PSUReference objects
        from src.models.schemas import PSUReference
        psu_list = []
        for row in psus:
            psu_list.append(PSUReference(
                id=row.id,
                name=row.name,
                wattage=row.wattage,
                efficiency_rating=row.efficiency_rating,
                modular=row.modular,
                price=row.price,
                search_keywords=list(row.search_keywords) if row.search_keywords else [],
                normalized_name=row.normalized_name
            ))
        
        matcher = PSUMatcher(psu_list)
        
        print("=" * 70)
        print("PSU MATCH RESULTS:")
        print("=" * 70)
        
        # Get the match
        result = matcher.match_listing(full_text, 360.0)
        
        if result.psu:
            print(f"✅ MATCHED: {result.psu.name}")
            print(f"   ID: {result.psu.id}")
            print(f"   Wattage: {result.psu.wattage}W")
            print(f"   Confidence: {result.confidence:.1%}")
            print(f"   Method: {result.method}")
        else:
            print("❌ No PSU match found")
        
        # Check specific PSU
        print()
        print("=" * 70)
        print("CHECKING SPECIFIC PSUs:")
        print("=" * 70)
        
        # Check Xilence XP600R6
        xilence = session.execute(text(
            "SELECT * FROM psu_reference WHERE id = 8617"
        )).fetchone()
        
        if xilence:
            print(f"\nXilence XP600R6 (ID: {xilence.id}):")
            print(f"  Name: {xilence.name}")
            print(f"  Wattage: {xilence.wattage}W")
            print(f"  Keywords: {xilence.search_keywords}")
            
            # Check if "xilence" or "xp600" appears in text
            text_lower = full_text.lower()
            if 'xilence' in text_lower:
                print("  ✓ 'xilence' found in listing text")
            else:
                print("  ✗ 'xilence' NOT found in listing text")
                
            if 'xp600' in text_lower:
                print("  ✓ 'xp600' found in listing text")
            else:
                print("  ✗ 'xp600' NOT found in listing text")
        
        # Check KOLINK Core RGB
        kolink = session.execute(text(
            "SELECT * FROM psu_reference WHERE id = 7396"
        )).fetchone()
        
        if kolink:
            print(f"\nKOLINK Core RGB (ID: {kolink.id}):")
            print(f"  Name: {kolink.name}")
            print(f"  Wattage: {kolink.wattage}W")
            print(f"  Keywords: {kolink.search_keywords}")
            
            text_lower = full_text.lower()
            if 'kolink' in text_lower:
                print("  ✓ 'kolink' found in listing text")
            else:
                print("  ✗ 'kolink' NOT found in listing text")
                
            if 'core' in text_lower:
                print("  ✓ 'core' found in listing text")
            else:
                print("  ✗ 'core' NOT found in listing text")
        
        # Show extracted PSU section from text
        print()
        print("=" * 70)
        print("PSU EXTRACTION DEBUG:")
        print("=" * 70)
        
        import re
        normalized = full_text.lower()
        
        # Find PSU context
        psu_pos = -1
        for kw in ['psu', 'barosana', 'barošana', 'block', 'bloks', 'barošanas', 'barošana']:
            pos = normalized.find(kw)
            if pos != -1:
                psu_pos = pos
                break
        
        if psu_pos != -1:
            start = max(0, psu_pos - 100)
            end = min(len(full_text), psu_pos + 200)
            psu_section = full_text[start:end]
            print(f"Text around 'PSU' keyword:")
            print(psu_section)
        else:
            print("No PSU keyword found in text")

if __name__ == "__main__":
    main()
