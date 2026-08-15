#!/usr/bin/env python3
"""Debug SSD matching for lphjf."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# Full listing text
listing_text = """Pārdod datoru. MSI MAG B650 TOMAHAWK WIFI
AMD Ryzen 7 8700F
RAM 32GB DDR5
SSD Kingston NV2 2TB
PSU Cooler Master V1200
Videokarte: Powercolor red devil RX6800XT 16gb
Procesors: Ryzen 7 8700F
Pamat plate: MSI MAG B650 TOMAHAWK WIFI
Video: Powercolor red devil RX6800XT 16gb
Operatīvā atmiņa, Gb: 32
HDD apjoms, Gb: 2000"""

full_text = listing_text
text_lower = full_text.lower()
normalized = normalize_text(full_text)

config = AppConfig()
init_database(config.database)
db = get_db_manager()

def _extract_ssd_capacity(text):
    """Extract SSD capacity from text."""
    import re
    # Look for TB patterns
    tb_match = re.search(r'(\d+)\s*TB', text, re.IGNORECASE)
    if tb_match:
        return int(tb_match.group(1)) * 1000
    # Look for GB patterns near SSD keywords
    gb_match = re.search(r'(\d+)\s*GB', text, re.IGNORECASE)
    if gb_match:
        return int(gb_match.group(1))
    return None

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)
    ssd_matcher = SSDMatcher(ssds)
    
    print("="*60)
    print("SSD MATCHER DEBUG")
    print("="*60)
    
    ssd_capacity = _extract_ssd_capacity(full_text)
    print(f"Extracted SSD capacity: {ssd_capacity} GB")
    
    # Try matching
    ssd_match = ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
    
    print(f"\nMatched SSD: {ssd_match.ssd.model if ssd_match.ssd else 'None'} (ID: {ssd_match.ssd.id if ssd_match.ssd else 'N/A'})")
    print(f"Brand: {ssd_match.ssd.brand if ssd_match.ssd else 'N/A'}")
    print(f"Capacity: {ssd_match.ssd.capacity_gb if ssd_match.ssd else 'N/A'} GB")
    print(f"Method: {ssd_match.method}")
    print(f"Confidence: {ssd_match.confidence}")
    
    # Now check computer_matcher acceptance logic
    if ssd_match.ssd:
        print("\n" + "="*60)
        print("COMPUTER_MATCHER ACCEPTANCE LOGIC")
        print("="*60)
        
        ssd_brand = normalize_text(ssd_match.ssd.brand)
        ssd_model = normalize_text(ssd_match.ssd.model)
        
        print(f"SSD brand: '{ssd_brand}'")
        print(f"SSD model: '{ssd_model}'")
        
        has_brand = ssd_brand in normalized
        print(f"has_brand ({ssd_brand} in normalized): {has_brand}")
        
        # Check model match
        has_model_in_text = ssd_model in normalized
        print(f"has_model_in_text ({ssd_model} in normalized): {has_model_in_text}")
        
        # Check for model in text more flexibly
        model_parts = ssd_match.ssd.model.split()
        for part in model_parts:
            part_norm = normalize_text(part)
            if part_norm in normalized and len(part_norm) >= 2:
                print(f"  Model part '{part_norm}' found in text")
        
        is_exact = ssd_match.method.split('+')[0] == 'exact'
        is_model_part = 'model_part' in ssd_match.method
        is_nv2_match = 'nv2_match' in ssd_match.method
        
        print(f"\nis_exact: {is_exact}")
        print(f"is_model_part: {is_model_part}")
        print(f"is_nv2_match: {is_nv2_match}")
        
        # Determine if specific
        is_specific_ssd = False
        if is_exact:
            is_specific_ssd = True
            print("\nSSD is specific: exact match")
        elif is_model_part and has_brand:
            # Check if model actually appears in text
            if has_model_in_text:
                is_specific_ssd = True
                print("\nSSD is specific: model_part + brand + model in text")
            else:
                print("\nSSD NOT specific: model_part + brand but model NOT in text")
        elif is_nv2_match and has_brand:
            is_specific_ssd = True
            print("\nSSD is specific: nv2_match + brand")
        else:
            print("\nSSD NOT specific: no criteria met")
        
        print(f"\nFinal is_specific_ssd: {is_specific_ssd}")
