# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

# Force reload
import importlib
import src.scraper.ssd_matcher
importlib.reload(src.scraper.ssd_matcher)

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

print(f"Total SSDs: {len(ssds)}")

matcher = SSDMatcher(ssds)

# Test
text = "netac 256gb ssd"
print(f"\nTesting: '{text}'")

result = matcher.match(text, "")
print(f"Result: {result}")
print(f"SSD: {result.ssd}")
if result.ssd:
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  Capacity: {result.ssd.capacity_gb}")
print(f"Confidence: {result.confidence}")
print(f"Method: {result.method}")
