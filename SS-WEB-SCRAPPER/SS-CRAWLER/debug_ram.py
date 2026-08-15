#!/usr/bin/env python3
"""Debug RAM matching for fgfbp."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.scraper.ram_matcher import RAMMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# The actual text from the listing
listing_text = """Pārdod datoru. Asus prime b760m-a wifi
intel i5 14400f
ram g. Skill f4 3000 c16d -32gb
ssd xlr8 cs3140 nvme m. 2 -1tb 7500mb/s
hdd seagate st2000nm0011 -2tb
aio cougar poseidon vistek argb 240
psu xfx xtr750 80+gold
gpu radeon rx 9060 xt 16gb
case ft418 white
Procesors:
I5 14400F
Procesora frekvence, Ghz:
4.50
Pamat plate:
Asus prime b760m-a wifi
Video:
Radeon rx 9060 xt
Operatīvā atmiņa, Gb:
32
HDD apjoms, Gb:
2000"""

normalized = normalize_text(listing_text)
print(f"Normalized text:\n{normalized}\n")

# Test G.Skill pattern detection
has_gskill = 'gskill' in normalized
print(f"'gskill' in normalized: {has_gskill}")

gskill_patterns = [
    r'f(\d+)-(\d+)c(\d+)d-?(\d+)(\w+)',  # f4-3200c16d-32gtz or f4-3200c16d32gtz
    r'f(\d+)\s+(\d+)\s*c(\d+)d\s*-?(\d+)(\w+)',  # f4 3200 c16d 32gtz
]

for i, pattern in enumerate(gskill_patterns):
    match = re.search(pattern, normalized)
    print(f"Pattern {i+1}: {pattern}")
    print(f"  Match: {match}")
    if match:
        print(f"  Groups: {match.groups()}")

# Simple pattern
simple_match = re.search(r'f\d+[\s-]?\d+c\d+d', normalized)
print(f"\nSimple pattern 'f\\d+[\\s-]?\\d+c\\d+d': {simple_match}")
if simple_match:
    print(f"  Matched: {simple_match.group()}")

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    ram_matcher = RAMMatcher(rams)
    
    # Test match with different parameters
    print("\n" + "="*60)
    print("Testing RAM matching...")
    print("="*60)
    
    # Test 1: No extracted values
    result1 = ram_matcher.match_listing(listing_text)
    print(f"\nTest 1 - No extracted values:")
    print(f"  Matched: {result1.ram.name if result1.ram else 'None'}")
    print(f"  Method: {result1.method}")
    print(f"  Confidence: {result1.confidence}")
    
    # Test 2: With extracted capacity
    result2 = ram_matcher.match_listing(listing_text, extracted_capacity=32)
    print(f"\nTest 2 - With extracted_capacity=32:")
    print(f"  Matched: {result2.ram.name if result2.ram else 'None'}")
    print(f"  Method: {result2.method}")
    print(f"  Confidence: {result2.confidence}")
    
    # Test 3: With extracted capacity and DDR
    result3 = ram_matcher.match_listing(listing_text, extracted_capacity=32, extracted_ddr="DDR4")
    print(f"\nTest 3 - With extracted_capacity=32, extracted_ddr='DDR4':")
    print(f"  Matched: {result3.ram.name if result3.ram else 'None'}")
    print(f"  Method: {result3.method}")
    print(f"  Confidence: {result3.confidence}")
    
    # Test 4: With all extracted values
    result4 = ram_matcher.match_listing(listing_text, extracted_capacity=32, extracted_ddr="DDR4", extracted_speed="DDR4-3000")
    print(f"\nTest 4 - With extracted_capacity=32, extracted_ddr='DDR4', extracted_speed='DDR4-3000':")
    print(f"  Matched: {result4.ram.name if result4.ram else 'None'}")
    print(f"  Method: {result4.method}")
    print(f"  Confidence: {result4.confidence}")
