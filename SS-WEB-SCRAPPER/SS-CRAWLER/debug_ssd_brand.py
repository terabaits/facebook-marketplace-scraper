# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

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

# Test cases
tests = [
    ("pcneb", "netac 256gb ssd"),
    ("lphjf", "Kinsgotn NV2 2tb"),
]

for test_id, text in tests:
    print(f"\n{'='*60}")
    print(f"Test: {test_id} - '{text}'")
    print('='*60)
    
    normalized = normalize_text(text)
    print(f"Normalized: '{normalized}'")
    
    # Check tokens
    tokens = matcher._extract_ssd_tokens(text)
    print(f"Extracted tokens: {tokens}")
    
    # Check capacity
    capacity = matcher._extract_capacity(text)
    print(f"Extracted capacity: {capacity}")
    
    # Check match
    result = matcher.match(text, "")
    if result.ssd:
        print(f"Matched: {result.ssd.brand} {result.ssd.model}")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.method}")
    else:
        print("No match")

# Check if Netac SSDs exist
print("\n\n=== Netac SSDs in Database ===")
for ssd in ssds:
    if ssd.brand and 'netac' in ssd.brand.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} ({ssd.capacity_gb}GB)")
        
# Check Kingston NV2
print("\n\n=== Kingston NV2 SSDs ===")
for ssd in ssds:
    if ssd.brand and 'kingston' in ssd.brand.lower() and 'nv2' in ssd.model.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} ({ssd.capacity_gb}GB)")
