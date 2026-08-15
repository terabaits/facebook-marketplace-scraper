# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.scraper.motherboard_matcher import MotherboardMatcher
from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    motherboards = MotherboardRepository.get_all(session)
    matcher = MotherboardMatcher(motherboards)
    
    # Check what brand_model_names contains for H310 boards
    h310_names = [(name, mb.id) for name, mb in matcher.brand_model_names.items() 
                   if 'h310' in name.lower() and 'gigabyte' in name.lower()]
    
    print("Gigabyte H310 boards in brand_model_names:")
    for name, mb_id in sorted(h310_names, key=lambda x: len(x[0]), reverse=True)[:10]:
        print(f"  '{name}' -> ID {mb_id}")
    
    # Test the actual text
    text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Mat. pl. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""
    
    # Normalize
    normalized = normalize_text(text)
    print(f"\nNormalized text contains 'gigabyte h310m s2h 2.0': {'gigabyte h310m s2h 2.0' in normalized}")
    
    # Check if any exact match would work
    print("\n" + "="*60)
    print("Checking exact matches:")
    sorted_names = sorted(matcher.brand_model_names.items(), key=lambda x: len(x[0]), reverse=True)
    found_exact = None
    for name, mb in sorted_names[:100]:  # Check first 100
        if name in normalized:
            found_exact = (name, mb)
            print(f"EXACT MATCH: '{name}' -> {mb.brand} {mb.model} (ID {mb.id})")
            break
    
    if not found_exact:
        print("No exact match found in first 100 entries")
        
    # Now test with the actual text
    print("\n" + "="*60)
    print("Testing with full text (with Mat. pl.):")
    result = matcher.match_listing(text)
    if result.motherboard:
        print(f"Matched: {result.motherboard.brand} {result.motherboard.model} (ID {result.motherboard.id})")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.method}")
    else:
        print("No match")
