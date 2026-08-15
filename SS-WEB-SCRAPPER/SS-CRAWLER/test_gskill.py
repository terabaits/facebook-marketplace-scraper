# -*- coding: utf-8 -*-
"""Test G.Skill RAM matching."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.scraper.ram_matcher import RAMMatcher
from src.database.repository import RAMReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    matcher = RAMMatcher(rams)
    
    # Test cases
    test_cases = [
        ("G.Skill F4-3200C16D-32GTZ", "pardod datoru operativa atmina gskill f43200c16d32gtz 32gb"),
        ("G.Skill Aegis", "pardod datoru operativa atmina gskill aegis 32gb ddr4"),
    ]
    
    print("=== G.Skill RAM Test ===\n")
    for expected, text in test_cases:
        result = matcher.match_listing(text, extracted_capacity=32, extracted_ddr="DDR4")
        matched = result.ram.name if result.ram else "None"
        print(f"Expected: {expected}")
        print(f"Got: {matched}")
        print(f"Method: {result.method}")
        print(f"Confidence: {result.confidence}\n")

print("Done!")
