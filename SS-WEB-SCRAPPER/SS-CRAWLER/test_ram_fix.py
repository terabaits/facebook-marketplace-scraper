# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.scraper.ram_matcher import RAMMatcher
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    matcher = RAMMatcher(rams)

    # Test HyperX matching
    text = "Pārdod datoru. Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz"
    
    print("=== HyperX RAM Test ===")
    print(f"Text: {text}")
    
    result = matcher.match_listing(text, extracted_capacity=16, extracted_ddr="DDR4", extracted_speed="3200")
    
    if result.ram:
        print(f"Matched: {result.ram.name}")
        print(f"ID: {result.ram.id}")
        print(f"Method: {result.method}")
        print(f"Confidence: {result.confidence}")
        
        is_correct = result.ram.id == 3289
        print(f"\nExpected: ID 3289 (Kingston HyperX 16 GB)")
        print(f"Status: {'PASS' if is_correct else 'FAIL'}")
    else:
        print("No match found - FAIL")
