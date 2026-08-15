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

# fpokc SSD description
desc = """Cietie diski: SSD Crucial MX500 1TB"""

print("Testing fpokc SSD...")
normalized = normalize_text(desc)
print(f"Text: '{desc}'")
print(f"Normalized: '{normalized}'")

# Check SSDs in database
print("\n=== SSDs with 'MX500' ===")
for ssd in ssds:
    if ssd.model and 'mx500' in ssd.model.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} - {ssd.capacity_gb}GB")

print("\n=== SSDs with 'SSD' in name ===")
for ssd in ssds:
    if 'ssd' in ssd.model.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model}")

# Match
result = matcher.match_listing(desc, extracted_capacity=1000)
print(f"\nMatch result:")
if result.ssd:
    print(f"  ID: {result.ssd.id}")
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  Method: {result.method}")
else:
    print("  No match")
