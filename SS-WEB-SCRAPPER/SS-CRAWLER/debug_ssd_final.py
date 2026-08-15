# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSUReferenceRepository, CaseReferenceRepository,
    MotherboardReferenceRepository, MonitorReferenceRepository
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
        psus=PSUReferenceRepository.get_all(session),
        cases=CaseReferenceRepository.get_all(session),
        motherboards=MotherboardReferenceRepository.get_all(session),
        monitors=MonitorReferenceRepository.get_all(session)
    )

# Test text
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""
normalized = normalize_text(text)

print("Testing SSD matching...")

# Simulate what computer_matcher does
full_text = text
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"SSD Capacity extracted: {ssd_capacity}")

ssd_match = cm.ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
print(f"ssd_match.ssd: {ssd_match.ssd}")

if ssd_match.ssd:
    print(f"\nSSD found: {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"  Method: {ssd_match.method}")
    
    ssd_brand = normalize_text(ssd_match.ssd.brand)
    ssd_model = normalize_text(ssd_match.ssd.model)
    has_brand = ssd_brand in normalized
    
    print(f"\n  ssd_brand: '{ssd_brand}'")
    print(f"  has_brand (in normalized): {has_brand}")
    
    # Check model match
    has_model_in_text = False
    if ssd_model in normalized:
        has_model_in_text = True
    else:
        model_parts = re.split(r'[\/\s\-]+', ssd_model)
        for part in model_parts:
            if len(part) > 3 and part in normalized:
                has_model_in_text = True
                break
    
    print(f"  ssd_model: '{ssd_model}'")
    print(f"  has_model_in_text: {has_model_in_text}")
    
    # Check conditions
    is_exact = ssd_match.method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in ssd_match.method
    is_capacity_match = 'capacity_exact' in ssd_match.method or 'capacity_near' in ssd_match.method
    
    print(f"\n  is_exact: {is_exact}")
    print(f"  is_model_part: {is_model_part}")
    print(f"  is_capacity_match: {is_capacity_match}")
    
    # Check SSD context
    ssd_brand_in_ssd_context = False
    ssd_brand_lower = ssd_match.ssd.brand.lower()
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'disk', 'cietie']
    for kw in ssd_keywords:
        if kw in normalized:
            kw_pos = normalized.find(kw)
            context_start = max(0, kw_pos - 40)
            context_end = min(len(normalized), kw_pos + 40)
            context = normalized[context_start:context_end]
            if ssd_brand_lower in context:
                ssd_brand_in_ssd_context = True
                print(f"\n  Brand found in SSD context (near '{kw}')")
                break
    
    print(f"\n  ssd_brand_in_ssd_context: {ssd_brand_in_ssd_context}")
    
    is_specific_ssd = is_exact or (is_model_part and has_model_in_text and has_brand) or (is_capacity_match and ssd_brand_in_ssd_context)
    print(f"\n  is_specific_ssd: {is_specific_ssd}")
    
    if is_specific_ssd:
        print("\n  -> SSD WOULD BE ACCEPTED")
    else:
        print("\n  -> SSD WOULD BE REJECTED (using generic fallback)")
