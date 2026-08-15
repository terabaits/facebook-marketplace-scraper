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

# Simulate what computer_matcher does
text = "Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"
normalized = normalize_text(text)

print("Testing SSD matching in computer_matcher context...")
print(f"Full text: {text[:80]}...")
print(f"Normalized: {normalized[:80]}...")

# Check if netac is in normalized
print(f"\n'netac' in normalized: {'netac' in normalized}")

# Check SSD tokens
tokens = matcher._extract_ssd_tokens(text)
print(f"SSD tokens: {tokens}")

# Check capacity
patterns = [
    r'netac\s+\d{3,4}\s*gb',
    r'(?:netac|kingston|samsung)\s+(?:[a-z0-9\-]+\s+)?(\d{3,4})\s*gb',
]
capacity = None
for pattern in patterns:
    match = re.search(pattern, normalized)
    if match:
        print(f"Capacity pattern matched: {match.group()}")
        cap_match = re.search(r'(\d{3,4})', match.group())
        if cap_match:
            capacity = int(cap_match.group(1))
            break

print(f"Capacity: {capacity}")

# Call match_listing
print("\n=== Calling match_listing ===")
result = matcher.match_listing(text, extracted_capacity=capacity)
print(f"Result SSD: {result.ssd}")
if result.ssd:
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
    
    # Check if computer_matcher would accept this
    ssd_brand = normalize_text(result.ssd.brand)
    ssd_model = normalize_text(result.ssd.model)
    has_brand = ssd_brand in normalized
    has_model = ssd_model in normalized
    
    print(f"\ncomputer_matcher checks:")
    print(f"  ssd_brand (normalized): '{ssd_brand}'")
    print(f"  ssd_model (normalized): '{ssd_model}'")
    print(f"  has_brand: {has_brand}")
    print(f"  has_model: {has_model}")
    
    is_exact = result.method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in result.method
    is_specific = is_exact or (is_model_part and has_model and has_brand)
    
    print(f"  is_exact: {is_exact}")
    print(f"  is_model_part: {is_model_part}")
    print(f"  is_specific_ssd: {is_specific}")
