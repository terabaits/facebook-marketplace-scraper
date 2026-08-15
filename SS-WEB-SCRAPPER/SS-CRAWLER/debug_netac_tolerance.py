# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

matcher = SSDMatcher(ssds)

# Test tolerance calculation
extracted_capacity = 256
tolerance = min(max(extracted_capacity * 0.1, 20), 100)
print(f"Extracted capacity: {extracted_capacity}")
print(f"Tolerance: {tolerance}")
print(f"Valid range: {extracted_capacity - tolerance} to {extracted_capacity + tolerance}")

# Check Netac candidates
print("\nNetac SSDs within tolerance:")
if 'netac' in matcher.brand_to_ssds:
    for ssd in matcher.brand_to_ssds['netac']:
        if ssd.capacity_gb:
            diff = abs(extracted_capacity - ssd.capacity_gb)
            within = diff <= tolerance
            print(f"  {ssd.model} {ssd.capacity_gb}GB - diff: {diff}, within tolerance: {within}")
