# -*- coding: utf-8 -*-
"""Debug full SSD flow for fpokc."""
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

# Full fpokc text
text = """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini
Dators ir pilnībā darba kārtībā.
Cena 500 EUR.
Rīga"""

normalized = normalize_text(text)
print(f"Full normalized:\n{normalized}\n")

# Step 1: Extract SSD capacity
print("=== Step 1: Capacity Extraction ===")
text_lower = normalized.lower()

# Check combined storage patterns
combined_patterns = [
    r'\(\s*ssd\s*\+\s*hdd\s*\)',
    r'\(\s*hdd\s*\+\s*ssd\s*\)',
    r'(?:\d+\s*(?:gb|tb)\s+)?ssd\s*\+\s*\d+\s*(?:gb|tb)\s+hdd',
    r'total.*storage',
]
combined_match = False
for pattern in combined_patterns:
    if re.search(pattern, text_lower, re.IGNORECASE):
        combined_match = True
        print(f"  Combined storage pattern matched: {pattern}")
        break

# TB patterns
tb_patterns = [
    r'(\d+(?:\.\d+)?)\s*tb\s+ssd\b',
    r'\bssd\s+(\d+(?:\.\d+)?)\s*tb\b',
    r'\bssd.*?crucial.*?mx500.*?(\d+(?:\.\d+)?)\s*tb',
    r'crucial.*?mx500.*?(\d+(?:\.\d+)?)\s*tb',
]

ssd_capacity = None
for pattern in tb_patterns:
    match = re.search(pattern, text_lower, re.IGNORECASE)
    if match:
        try:
            ssd_capacity = int(float(match.group(1)) * 1000)
            print(f"  Capacity extracted: {ssd_capacity}GB (pattern: {pattern[:50]})")
            break
        except ValueError:
            pass

if not ssd_capacity:
    print("  No capacity extracted!")
else:
    print(f"  Final capacity: {ssd_capacity}")

# Step 2: SSD Matcher
print(f"\n=== Step 2: SSD Matcher ===")
ssd_match = matcher.match_listing(text, extracted_capacity=ssd_capacity)
if ssd_match.ssd:
    print(f"  Matched: ID {ssd_match.ssd.id} - {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"  Confidence: {ssd_match.confidence}")
    print(f"  Method: {ssd_match.method}")
else:
    print("  No SSD match from matcher!")

# Step 3: Check what the fallback would pick
print(f"\n=== Step 3: Fallback Analysis ===")
if not ssd_match.ssd and ssd_capacity:
    print("  Would enter fallback...")
    
# Check which SSDs have matching brand in text
print("  Brands found in text:")
for brand in ['crucial', 'kingston', 'samsung', 'wd', 'gigabyte', 'intel']:
    if brand in text_lower:
        brand_pos = text_lower.find(brand)
        window_start = max(0, brand_pos - 40)
        window_end = min(len(text_lower), brand_pos + 40)
        window = text_lower[window_start:window_end]
        has_ssd = any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2', 'disk'])
        print(f"    {brand}: pos={brand_pos}, SSD nearby={has_ssd}")
