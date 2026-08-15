# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

matcher = SSDMatcher(ssds)

# Full text from pcneb.html
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""
full_text = text
normalized = normalize_text(text)

# Simulate computer_matcher logic
ssd_capacity = 256  # Assume extracted
ssd_match = matcher.match_listing(full_text, extracted_capacity=ssd_capacity)

print(f"ssd_match.ssd: {ssd_match.ssd}")
print(f"ssd_match.confidence: {ssd_match.confidence}")
print(f"ssd_match.method: {ssd_match.method}")

if ssd_match.ssd:
    print(f"\nSSD found: {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    
    ssd_brand = normalize_text(ssd_match.ssd.brand)
    ssd_model = normalize_text(ssd_match.ssd.model)
    has_brand = ssd_brand in normalized
    has_model = ssd_model in normalized
    
    print(f"ssd_brand: '{ssd_brand}'")
    print(f"ssd_model: '{ssd_model}'")
    print(f"has_brand: {has_brand}")
    print(f"has_model: {has_model}")
    
    is_exact = ssd_match.method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in ssd_match.method
    is_capacity_match = 'capacity_exact' in ssd_match.method or 'capacity_near' in ssd_match.method
    
    print(f"is_exact: {is_exact}")
    print(f"is_model_part: {is_model_part}")
    print(f"is_capacity_match: {is_capacity_match}")
    
    is_specific_ssd = is_exact or (is_model_part and has_model and has_brand) or (is_capacity_match and has_brand)
    print(f"is_specific_ssd: {is_specific_ssd}")
else:
    print("\nNo SSD matched by match_listing")
