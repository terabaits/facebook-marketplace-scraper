# -*- coding: utf-8 -*-
"""Debug full SSD flow in computer_matcher."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository,
    MotherboardRepository, MonitorRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cm = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSURepository.get_all(session),
        cases=CaseRepository.get_all(session),
        motherboards=MotherboardRepository.get_all(session),
        monitors=MonitorRepository.get_all(session)
    )

# fpokc text
text = """Cietie diski: SSD Crucial MX500 1TB"""
normalized = normalize_text(text)

print("Testing full SSD flow...")
print(f"Text: {text}")
print(f"Normalized: {normalized}\n")

# Step 1: Extract capacity
ssd_capacity = cm._extract_ssd_capacity(text)
print(f"Step 1 - Extracted capacity: {ssd_capacity}")

# Step 2: SSD matcher
print(f"\nStep 2 - SSD matcher:")
ssd_match = cm.ssd_matcher.match_listing(text, extracted_capacity=ssd_capacity)
if ssd_match.ssd:
    print(f"  Matched: ID {ssd_match.ssd.id} - {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"  Confidence: {ssd_match.confidence}")
    print(f"  Method: {ssd_match.method}")
else:
    print("  No match from SSD matcher")

# Step 3: Check is_specific_ssd logic
print(f"\nStep 3 - is_specific_ssd check:")
if ssd_match.ssd:
    is_exact = ssd_match.confidence >= 0.9
    is_model_part = 'model_part' in ssd_match.method
    is_capacity_match = 'capacity' in ssd_match.method or 'capacity_exact' in ssd_match.method
    
    # Check model parts
    model_lower = ssd_match.ssd.model.lower()
    model_parts = re.split(r'[/\s\-]+', model_lower)
    has_model_in_text = False
    for part in model_parts:
        if len(part) >= 3 and part in normalized:
            has_model_in_text = True
            print(f"    Model part '{part}' in text")
    
    # Check brand
    brand_lower = ssd_match.ssd.brand.lower()
    has_brand = brand_lower in normalized
    print(f"    Brand '{brand_lower}' in text: {has_brand}")
    
    # Check brand in SSD context
    ssd_brand_in_ssd_context = False
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'disk', 'cietie']
    for kw in ssd_keywords:
        if kw in normalized:
            kw_pos = normalized.find(kw)
            context_start = max(0, kw_pos - 40)
            context_end = min(len(normalized), kw_pos + 40)
            context = normalized[context_start:context_end]
            if brand_lower in context:
                ssd_brand_in_ssd_context = True
                print(f"    Brand in SSD context (kw '{kw}')")
                break
    
    is_specific_ssd = is_exact or (is_model_part and has_model_in_text and has_brand) or (is_capacity_match and ssd_brand_in_ssd_context)
    print(f"\n    is_exact: {is_exact}")
    print(f"    is_model_part: {is_model_part}")
    print(f"    has_model_in_text: {has_model_in_text}")
    print(f"    has_brand: {has_brand}")
    print(f"    is_capacity_match: {is_capacity_match}")
    print(f"    ssd_brand_in_ssd_context: {ssd_brand_in_ssd_context}")
    print(f"    >>> is_specific_ssd: {is_specific_ssd}")

# Step 4: If not specific, check fallback
print(f"\nStep 4 - Fallback logic:")
if not ssd_match.ssd or not True:  # Simulate not is_specific_ssd
    print("  Would enter fallback...")
    
    # Check what SSDs match "gigabyte" (from motherboard line)
    text_lower = normalized.lower()
    print(f"  Checking for 'gigabyte' in text: {'gigabyte' in text_lower}")
    if 'gigabyte' in text_lower:
        print("  'Gigabyte' SSDs in database:")
        for ssd in cm.ssds.values():
            if 'gigabyte' in ssd.brand.lower():
                print(f"    ID {ssd.id}: {ssd.brand} {ssd.model}")
