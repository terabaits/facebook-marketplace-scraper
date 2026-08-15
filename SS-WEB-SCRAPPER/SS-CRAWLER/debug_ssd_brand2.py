# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
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

print(f"Loaded {len(ssds)} SSDs")

matcher = SSDMatcher(ssds)

# Test cases
tests = [
    ("pcneb", "netac 256gb ssd"),
]

for test_id, text in tests:
    print(f"\n{'='*60}")
    print(f"Test: {test_id} - '{text}'")
    print('='*60)
    
    normalized = normalize_text(text)
    print(f"Normalized: '{normalized}'")
    
    # Check tokens
    try:
        tokens = matcher._extract_ssd_tokens(text)
        print(f"Extracted tokens: {tokens}")
    except Exception as e:
        print(f"Token extraction error: {e}")
    
    # Check capacity
    try:
        capacity = matcher._extract_capacity(text)
        print(f"Extracted capacity: {capacity}")
    except Exception as e:
        print(f"Capacity extraction error: {e}")
    
    # Check match
    try:
        result = matcher.match(text, "")
        if result.ssd:
            print(f"Matched: {result.ssd.brand} {result.ssd.model}")
            print(f"Confidence: {result.confidence}")
            print(f"Method: {result.method}")
        else:
            print("No match")
    except Exception as e:
        import traceback
        print(f"Match error: {e}")
        traceback.print_exc()

print("\n\nDone!")
