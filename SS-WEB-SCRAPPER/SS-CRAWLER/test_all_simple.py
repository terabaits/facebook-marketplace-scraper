# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository, MotherboardRepository
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("Loading CPUs...")
    cpus = CPURepository.get_all(session)
    cpu_matcher = CPUMatcher(cpus)
    print(f"Loaded {len(cpus)} CPUs")
    
    print("\nLoading motherboards...")
    mobos = MotherboardRepository.get_all(session)
    mb_matcher = MotherboardMatcher(mobos)
    print(f"Loaded {len(mobos)} motherboards")
    
    # Test 1: fcddo CPU
    print("\n" + "=" * 70)
    print("Test 1: fcddo CPU - should be i5-4460, not i5-4460S")
    print("=" * 70)
    fcddo_text = "pardod datoru procesors intel core i54460 matesplate msi h81m eco"
    result = cpu_matcher.match(fcddo_text)
    if result.cpu:
        print(f"Got: {result.cpu.cpu_name} (ID: {result.cpu.id})")
        is_correct = result.cpu.id == 246  # i5-4460
        print(f"Status: {'PASS' if is_correct else 'FAIL'}")
    else:
        print("Status: FAIL - No match")
    
    # Test 2: alnnx Motherboard
    print("\n" + "=" * 70)
    print("Test 2: alnnx Motherboard - should be ID 7446 (TUF B450-PLUS GAMING)")
    print("=" * 70)
    alnnx_text = "pardod spelu datoru procesors amd ryzen 5 1600x matesplate asus tuf b450plus gaming operativa atmina hyperx fury ddr4 16gb"
    result = mb_matcher.match_listing(alnnx_text)
    if result.motherboard:
        print(f"Got: ID {result.motherboard.id} - {result.motherboard.brand} {result.motherboard.model}")
        is_correct = result.motherboard.id == 7446
        print(f"Status: {'PASS' if is_correct else 'FAIL'}")
    else:
        print("Status: FAIL - No match")

print("\nDone!")
