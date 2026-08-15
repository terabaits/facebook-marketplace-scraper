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

# The actual text from the listing
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500

Dators vel ar garantiju līdz šā gada beigām (PC veikals).

Dators atrodas Siguldā (Rīgā pievest var)."""

print("Testing actual pcneb.html text...")
print(f"Text length: {len(text)}")

# Extract capacity like computer_matcher does
import re
text_lower = text.lower()
capacity = None

# Check for SSD-specific patterns first
patterns = [
    r'(?:netac|kingston|samsung|wd|crucial|intel|adata)\s+(?:[a-z0-9\-]+\s+)?(\d{3,4})\s*gb',
]
for pattern in patterns:
    match = re.search(pattern, text_lower)
    if match:
        print(f"Pattern matched: {match.group()}")
        try:
            capacity = int(match.group(1))
            print(f"Capacity extracted: {capacity}")
            break
        except:
            pass

# Call match_listing
print("\nCalling match_listing...")
result = matcher.match_listing(text, extracted_capacity=capacity)

if result.ssd:
    print(f"\nMatched SSD: {result.ssd.brand} {result.ssd.model}")
    print(f"ID: {result.ssd.id}")
    print(f"Capacity: {result.ssd.capacity_gb}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.method}")
else:
    print("\nNo SSD matched")

# Check top candidates
print("\n=== Top 5 SSDs by score ===")
scores = []
normalized = normalize_text(text)
for ssd in matcher.ssds:
    if ssd.capacity_gb and abs(ssd.capacity_gb - 256) <= 100:
        score, method = matcher._score_ssd_match(ssd, normalized, 256)
        if score > 0:
            scores.append((score, ssd, method))

scores.sort(reverse=True)
for score, ssd, method in scores[:5]:
    print(f"  {ssd.brand} {ssd.model} {ssd.capacity_gb}GB: {score:.1f} ({method})")
