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

# Test text
text = "netac 256gb ssd"
normalized = normalize_text(text)
print(f"Text: '{text}'")
print(f"Normalized: '{normalized}'")

# Check candidates
if 'netac' in matcher.brand_to_ssds:
    print(f"\nFound {len(matcher.brand_to_ssds['netac'])} Netac SSDs")
    
    # Filter to capacity 256
    candidates = []
    for ssd in matcher.brand_to_ssds['netac']:
        if ssd.capacity_gb:
            tolerance = min(max(256 * 0.1, 20), 100)
            if abs(256 - ssd.capacity_gb) <= tolerance:
                candidates.append(ssd)
    
    print(f"Candidates within tolerance: {len(candidates)}")
    
    for ssd in candidates:
        print(f"\n--- Testing {ssd.model} {ssd.capacity_gb}GB ---")
        score, method = matcher._score_ssd_match(ssd, normalized, 256)
        print(f"Score: {score}, Method: '{method}'")
