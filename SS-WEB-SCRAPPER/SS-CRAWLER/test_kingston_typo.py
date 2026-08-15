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
    ("Kingston NV2", "kingston nv2 2tb ssd"),
    ("Kinsgotn typo", "kinsgotn nv2 2tb ssd"),
    ("Kinsgotn with model", "Kinsgotn NV2 2TB"),
]

for name, text in tests:
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Text: '{text}'")
    
    normalized = normalize_text(text)
    print(f"Normalized: '{normalized}'")
    
    result = matcher.match_listing(text, extracted_capacity=2000)
    
    if result.ssd:
        print(f"✓ Matched: {result.ssd.brand} {result.ssd.model}")
        print(f"  ID: {result.ssd.id}")
        print(f"  Capacity: {result.ssd.capacity_gb}GB")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Method: {result.method}")
    else:
        print("✗ No match")
