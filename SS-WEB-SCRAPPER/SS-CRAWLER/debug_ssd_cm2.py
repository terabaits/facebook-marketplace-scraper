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

# Check if 'netac' is in brand_to_ssds
print("Checking brand_to_ssds...")
if 'netac' in matcher.brand_to_ssds:
    print(f"  'netac' found with {len(matcher.brand_to_ssds['netac'])} SSDs")
else:
    print("  'netac' NOT found in brand_to_ssds")
    print(f"  Available brands: {list(matcher.brand_to_ssds.keys())[:20]}...")
