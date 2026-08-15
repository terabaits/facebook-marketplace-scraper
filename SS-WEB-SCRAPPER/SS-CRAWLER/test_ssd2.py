# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

matcher = SSDMatcher(ssds)

# Test text from pcneb.html
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500

Dators vel ar garantiju līdz šā gada beigām (PC veikals).

Dators atrodas Siguldā (Rīgā pievest var)."""

normalized = normalize_text(text)
print("Testing SSD matching...")

# Check for SSD capacity extraction
print("\n=== SSD capacity from _extract_ssd_capacity ===")
capacity = matcher._extract_ssd_capacity(text)
print(f"Capacity: {capacity}")

# Check for brand patterns in text
brands = [
    'samsung', 'kingston', 'netac', 'wd', 'western digital', 'crucial',
    'intel', 'adata', 'teamgroup', 'silicon power', 'seagate', 'toshiba'
]
print("\n=== Brand detection ===")
for brand in brands:
    if brand in normalized:
        print(f"Found: {brand}")

print("\n=== SSD Match ===")
result = matcher.match(text, "")
print(f"SSD: {result.ssd}")
print(f"Confidence: {result.confidence}")
print(f"Method: {result.method}")
