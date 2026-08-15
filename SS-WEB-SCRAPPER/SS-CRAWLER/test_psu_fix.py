#!/usr/bin/env python3
"""Quick test of PSU fix."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import init_database, get_session
from src.scraper.psu_matcher import PSUMatcher
from src.utils.config import AppConfig
from pathlib import Path
from sqlalchemy import text

def main():
    config = AppConfig.from_yaml('config.yaml')
    init_database(config.database)
    
    # Test text from listing
    test_text = "Barošanas bloks:XILENCE 600W"
    
    print("Testing PSU matcher...")
    print(f"Input text: {test_text}")
    print()
    
    with get_session() as session:
        psus = session.execute(text("SELECT * FROM psu_reference")).fetchall()
        
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
        result = matcher.match_listing(test_text, 360.0)
        
        if result.psu:
            print(f"MATCHED: {result.psu.name}")
            print(f"  ID: {result.psu.id}")
            print(f"  Expected: Xilence XP600R6 (ID 8617)")
            print(f"  Method: {result.method}")
            
            if result.psu.id == 8617:
                print("\n✅ CORRECT! Xilence matched!")
            else:
                print(f"\n❌ WRONG! Got ID {result.psu.id} instead of 8617")
        else:
            print("❌ No match found")

if __name__ == "__main__":
    main()
