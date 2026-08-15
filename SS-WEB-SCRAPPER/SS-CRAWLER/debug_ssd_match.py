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

# Test text from pcneb.html
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

normalized = normalize_text(text)
print("Normalized:", normalized)
print()

# Check extracted tokens
tokens = matcher._extract_ssd_tokens(text)
print("Extracted tokens:", tokens)

# Check capacity
print("\n=== Capacity extraction ===")
# Simulate what _extract_ssd_capacity does
import re
text_lower = text.lower()
capacity = None

# GB patterns
patterns = [
    r'(\d{3,4})\s*gb\s+ssd\b',
    r'ssd\s+(\d{3,4})\s*gb\b',
    r'nvme\s+(\d{3,4})\s*gb\b',
    r'm\.2\s+(\d{3,4})\s*gb\b',
    r'ssd.*?pcie.*?\d+.*?tb\b',
]

for pattern in patterns:
    match = re.search(pattern, text_lower)
    if match:
        print(f"Pattern '{pattern}' matched: {match.group()}")
        try:
            capacity = int(match.group(1))
            print(f"  Capacity: {capacity}")
            break
        except:
            pass

# SSD match
print("\n=== SSD Match Result ===")
result = matcher.match(text, "")
print(f"SSD: {result.ssd}")
print(f"Confidence: {result.confidence}")
print(f"Method: {result.method}")
