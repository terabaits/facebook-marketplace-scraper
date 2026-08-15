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

# Test fpokc
text = """Cietie diski: SSD Crucial MX500 1TB"""
print("Testing fpokc SSD matching...")
print(f"Text: '{text}'")

# Step 1: Extract capacity
import re
text_lower = text.lower()
capacity = None

# TB patterns
tb_patterns = [
    r'(\d+(?:\.\d+)?)\s*tb\s+ssd\b',
    r'\bssd\s+(\d+(?:\.\d+)?)\s*tb\b',
    r'\bssd.*?crucial.*?mx500.*?(\d+(?:\.\d+)?)\s*tb',
]
for pattern in tb_patterns:
    match = re.search(pattern, text_lower, re.IGNORECASE)
    if match:
        try:
            capacity = int(float(match.group(1)) * 1000)
            print(f"  Capacity extracted: {capacity}GB (pattern: {pattern[:40]})")
            break
        except ValueError:
            pass

if not capacity:
    print("  No capacity extracted!")

# Step 2: Match with SSD matcher
print("\n  Calling ssd_matcher.match_listing()...")
result = matcher.match_listing(text, extracted_capacity=capacity)
print(f"  Result: {result}")
if result.ssd:
    print(f"    SSD ID: {result.ssd.id}")
    print(f"    Brand: {result.ssd.brand}")
    print(f"    Model: {result.ssd.model}")
    print(f"    Method: {result.method}")
else:
    print("    No SSD matched!")

# Step 3: Check what SSDs would match "crucial mx500"
print("\n  SSDs matching 'crucial' and 'mx500':")
for ssd in ssds:
    if 'crucial' in ssd.brand.lower() and 'mx500' in ssd.model.lower():
        if ssd.capacity_gb == 1000:
            print(f"    ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
            print(f"      Normalized: {ssd.normalized_name}")
            print(f"      Keywords: {ssd.search_keywords[:2]}")
