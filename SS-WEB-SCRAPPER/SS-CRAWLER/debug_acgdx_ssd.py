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

# Test acgdx SSD text
text = """SSD: 1TB Kingston NV1"""

print("Testing acgdx SSD matching...")
print(f"Text: '{text}'")

normalized = normalize_text(text)
print(f"Normalized: '{normalized}'")

# Check tokens
tokens = matcher._extract_ssd_tokens(text)
print(f"Tokens: {tokens}")

# Check capacity
capacity = matcher._extract_capacity(text)
print(f"Capacity: {capacity}")

# Check match
result = matcher.match_listing(text, extracted_capacity=1000)
print(f"\nResult: {result.ssd}")
if result.ssd:
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  ID: {result.ssd.id}")
    print(f"  Capacity: {result.ssd.capacity_gb}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
else:
    print("  No match!")

# Check Kingston NV1 in database
print("\n=== Kingston NV1 SSDs ===")
for ssd in ssds:
    if ssd.brand and 'kingston' in ssd.brand.lower() and 'nv1' in ssd.model.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} ({ssd.capacity_gb}GB)")
