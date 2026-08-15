# -*- coding: utf-8 -*-
"""Debug ixefo SSD issue - why is Intel 760p matching?"""
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

# ixefo text
text = """Pārdod personīgo datoru.
Procesors: Intel Core i3-4130
Operatīvā atmiņa: DDR3 4GB
Cietie diski: SSD 120GB
Video karte: NVIDIA GeForce GT 520"""

print("=== ixefo SSD Debug ===")
normalized = normalize_text(text)
print(f"Full normalized:\n{normalized}\n")

# Check if "760" is in the text
if '760' in normalized:
    pos = normalized.find('760')
    print(f"'760' found at position {pos}")
    context = normalized[max(0, pos-20):min(len(normalized), pos+20)]
    print(f"Context: '{context}'")
    print("This is from 'i3-4130' becoming 'i34130' and extracting '760'")

# Check SSD extraction
print("\n=== SSD Extraction ===")
text_lower = normalized.lower()

# Combined storage patterns
combined_patterns = [
    r'\(\s*ssd\s*\+\s*hdd\s*\)',
    r'\(\s*hdd\s*\+\s*ssd\s*\)',
    r'(?:\d+\s*(?:gb|tb)\s+)?ssd\s*\+\s*\d+\s*(?:gb|tb)\s+hdd',
    r'total.*storage',
]
for pattern in combined_patterns:
    if re.search(pattern, text_lower, re.IGNORECASE):
        print(f"Combined storage pattern matched: {pattern}")

# Direct patterns
ssd_patterns = [
    r'(\d{3,4})\s*gb\s+ssd\b',
    r'ssd\s+(\d{3,4})\s*gb\b',
]
for pattern in ssd_patterns:
    match = re.search(pattern, text_lower, re.IGNORECASE)
    if match:
        print(f"Capacity extracted: {match.group(1)}GB (pattern: {pattern})")

# Check what SSDs have "760"
print("\n=== SSDs with '760' ===")
for ssd in ssds:
    if '760' in ssd.model:
        print(f"ID {ssd.id}: {ssd.brand} {ssd.model}")
        print(f"  Keywords: {ssd.search_keywords}")

# Run SSD match
print("\n=== SSD Match Result ===")
result = matcher.match_listing(text, extracted_capacity=120)
if result.ssd:
    print(f"Matched: ID {result.ssd.id} - {result.ssd.brand} {result.ssd.model}")
    print(f"Method: {result.method}")
else:
    print("No match")
