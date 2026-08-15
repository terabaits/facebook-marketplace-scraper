# -*- coding: utf-8 -*-
"""Test fixes for remaining issues."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository,
    MotherboardRepository, MonitorRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cm = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSURepository.get_all(session),
        cases=CaseRepository.get_all(session),
        motherboards=MotherboardRepository.get_all(session),
        monitors=MonitorRepository.get_all(session)
    )

# Test fpokc - SSD should be ID 453 (Crucial MX500 1000GB)
desc = """Cietie diski: SSD Crucial MX500 1TB"""

print("=== fpokc SSD Test ===")
print(f"Text: {desc}")
normalized = normalize_text(desc)
print(f"Normalized: {normalized}")

ssd_capacity = cm._extract_ssd_capacity(desc)
print(f"Extracted capacity: {ssd_capacity}")

# Direct SSD match
ssd_match = cm.ssd_matcher.match_listing(desc, extracted_capacity=ssd_capacity)
if ssd_match.ssd:
    print(f"Match: ID {ssd_match.ssd.id} - {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"Method: {ssd_match.method}")
else:
    print("No match")

# Check all crucial SSDs
print("\n=== Crucial MX500 in database ===")
for ssd in cm.ssds.values():
    if 'crucial' in ssd.brand.lower() and 'mx500' in ssd.model.lower():
        print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
        print(f"  Normalized: {ssd.normalized_name}")
        print(f"  Keywords: {ssd.search_keywords[:3]}")
