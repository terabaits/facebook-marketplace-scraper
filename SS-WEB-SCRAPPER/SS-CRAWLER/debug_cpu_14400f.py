# -*- coding: utf-8 -*-
"""Debug CPU i5-14400F matching."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository
from src.scraper.cpu_matcher import CPUMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cpus = CPURepository.get_all(session)
    matcher = CPUMatcher(cpus)
    
    # Test texts
    test_cases = [
        ("i5-14400F", "pardod datoru procesors intel core i514400f"),
        ("i5-14400", "pardod datoru procesors intel core i514400"),
    ]
    
    print("=== CPU F Suffix Test ===\n")
    for expected, text in test_cases:
        result = matcher.match(text)
        matched = result.cpu.cpu_name if result.cpu else "None"
        status = "PASS" if expected.lower() in matched.lower() else "FAIL"
        print(f"Expected: {expected}")
        print(f"Got: {matched}")
        print(f"Status: {status}\n")
