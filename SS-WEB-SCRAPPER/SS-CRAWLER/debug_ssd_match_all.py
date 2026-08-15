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

# Full text from pcneb.html
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

normalized = normalize_text(text)
print(f"Testing match_listing...")

result = matcher.match_listing(text, extracted_capacity=256)
print(f"Result: {result}")
if result.ssd:
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  Capacity: {result.ssd.capacity_gb}")
    print(f"  Score: {result.confidence}")
    print(f"  Method: {result.method}")
else:
    print("  No SSD matched")

# Check all SSDs with 256GB capacity
print("\n=== All SSDs with ~256GB capacity ===")
for ssd in matcher.ssds:
    if ssd.capacity_gb and abs(ssd.capacity_gb - 256) <= 10:
        score, method = matcher._score_ssd_match(ssd, normalized, 256)
        if score > 0:
            print(f"  {ssd.brand} {ssd.model} {ssd.capacity_gb}GB: {score:.1f} ({method})")
