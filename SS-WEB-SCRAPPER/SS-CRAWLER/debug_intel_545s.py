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
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500

Dators vel ar garantiju līdz šā gada beigām (PC veikals).

Dators atrodas Siguldā (Rīgā pievest var)."""

normalized = normalize_text(text)
print(f"Normalized: {normalized[:100]}...")

# Check if Intel is mentioned
print(f"\n'intel' in normalized: {'intel' in normalized}")
print(f"'netac' in normalized: {'netac' in normalized}")

# Check all SSDs
print("\n=== Top scoring SSDs ===")
scores = []
for ssd in matcher.ssds:
    score, method = matcher._score_ssd_match(ssd, normalized, 256)
    if score > 0:
        scores.append((score, ssd, method))

scores.sort(reverse=True)
for score, ssd, method in scores[:10]:
    print(f"  {ssd.brand} {ssd.model} {ssd.capacity_gb}GB: {score:.1f} ({method})")
