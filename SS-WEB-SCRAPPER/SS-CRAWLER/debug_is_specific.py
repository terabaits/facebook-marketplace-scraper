# -*- coding: utf-8 -*-
"""Debug is_specific_ssd logic."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

matcher = SSDMatcher(ssds)

# fpokc text
text = """Cietie diski: SSD Crucial MX500 1TB"""
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Extract capacity
extracted_capacity = 1000  # From TB extraction

# Get SSD match
ssd_match = matcher.match_listing(text, extracted_capacity=extracted_capacity)
print(f"\nSSD Match Result:")
print(f"  SSD: {ssd_match.ssd.brand} {ssd_match.ssd.model} (ID: {ssd_match.ssd.id})")
print(f"  Confidence: {ssd_match.confidence}")
print(f"  Method: {ssd_match.method}")

# Simulate is_specific_ssd logic
if ssd_match.ssd:
    is_exact = ssd_match.confidence >= 0.9
    is_model_part = 'model_part' in ssd_match.method
    is_capacity_match = 'capacity' in ssd_match.method or 'capacity_exact' in ssd_match.method
    
    # Check model parts in text
    model_lower = ssd_match.ssd.model.lower()
    model_parts = re.split(r'[/\s\-]+', model_lower)
    has_model_in_text = False
    for part in model_parts:
        if len(part) >= 3 and part in normalized:
            has_model_in_text = True
            print(f"    Model part '{part}' found in text")
    
    # Check brand in text
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
                print(f"    Brand in SSD context (kw '{kw}'): {context}")
                break
    
    is_specific_ssd = is_exact or (is_model_part and has_model_in_text and has_brand) or (is_capacity_match and ssd_brand_in_ssd_context)
    
    print(f"\n  is_exact: {is_exact}")
    print(f"  is_model_part: {is_model_part}")
    print(f"  has_model_in_text: {has_model_in_text}")
    print(f"  has_brand: {has_brand}")
    print(f"  is_capacity_match: {is_capacity_match}")
    print(f"  ssd_brand_in_ssd_context: {ssd_brand_in_ssd_context}")
    print(f"\n  >>> is_specific_ssd: {is_specific_ssd}")
