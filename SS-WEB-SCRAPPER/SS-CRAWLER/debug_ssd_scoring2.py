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
print(f"Normalized: {normalized}")

# Test Netac SSDs specifically
print("\n=== Netac SSD scoring ===")
if 'netac' in matcher.brand_to_ssds:
    for ssd in matcher.brand_to_ssds['netac']:
        if ssd.capacity_gb and abs(ssd.capacity_gb - 256) <= 30:
            score, method = matcher._score_ssd_match(ssd, normalized, 256)
            print(f"  {ssd.model} {ssd.capacity_gb}GB: Score={score:.1f}, Method='{method}'")
            
            # Debug: Check why score is low
            ssd_name = normalize_text(f"{ssd.brand} {ssd.model}")
            print(f"    SSD name: '{ssd_name}'")
            print(f"    In normalized: {ssd_name in normalized}")
            
            # Check model parts
            model_lower = ssd.model.lower()
            model_parts = re.split(r'[/\s\-]+', model_lower)
            for part in model_parts:
                if len(part) > 3:
                    print(f"    Part '{part}' in normalized: {part in normalized}")
