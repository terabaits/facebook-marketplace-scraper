# -*- coding: utf-8 -*-
"""Test the three fixes: alnnx (RAM + Motherboard), fcddo (CPU), kbdee (SSD)"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    # Initialize matchers
    computer_matcher = ComputerMatcher(session)

    print("=" * 70)
    print("Test 1: fcddo - CPU should be i5-4460 (not i5-4460S)")
    print("=" * 70)
    fcddo_text = """Pārdod datoru. Procesors: Intel Core i5-4460, Mātesplate: MSI H81M Eco,
Operatīvā atmiņa: DDR3 16GB, Video karte: GTX 1060 3GB"""

    fcddo_result = computer_matcher.match_listing(title="Pārdod datoru", description=fcddo_text, price=170)
    print(f"CPU: {fcddo_result.cpu.cpu.cpu_name if fcddo_result.cpu else 'None'}")
    if fcddo_result.cpu:
        print(f"  Expected: Intel Core i5-4460")
        print(f"  Got: {fcddo_result.cpu.cpu.cpu_name}")
        is_correct = 'i5-4460' in fcddo_result.cpu.cpu.cpu_name and '4460s' not in fcddo_result.cpu.cpu.cpu_name.lower()
        print(f"  Status: {'PASS' if is_correct else 'FAIL'}")

    print()
    print("=" * 70)
    print("Test 2: kbdee - SSD should be ID 817 Kingston A2000")
    print("=" * 70)
    kbdee_text = """Pārdod jaunu spēļu datoru. Procesors: Intel Core i7-14700KF, Mātesplate: Asus PRIME Z790-P,
Operatīvā atmiņa: Corsair Vengeance DDR4 32GB, Cietie diski: SSD M.2 1TB Kingston NVMe"""

    kbdee_result = computer_matcher.match_listing(title="Pārdod jaunu datoru", description=kbdee_text, price=1499)
    print(f"SSD: {kbdee_result.ssd.name if kbdee_result.ssd else 'None'}")
    if kbdee_result.ssd and kbdee_result.ssd.id:
        print(f"  Expected: ID 817 - Kingston A2000")
        print(f"  Got: ID {kbdee_result.ssd.id} - {kbdee_result.ssd.name}")
        print(f"  Status: {'PASS' if kbdee_result.ssd.id == 817 else 'FAIL'}")

    print()
    print("=" * 70)
    print("Test 3: alnnx - RAM should be ID 3289 Kingston HyperX 16GB")
    print("=" * 70)
    alnnx_text = """Pārdod spēļu datoru. Procesors: AMD Ryzen 5 1600X, Mātesplate: Asus TUF B450-PLUS GAMING,
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz"""

    alnnx_result = computer_matcher.match_listing(title="Pārdod spēļu datoru", description=alnnx_text, price=230)
    print(f"RAM: {alnnx_result.ram.name if alnnx_result.ram else 'None'}")
    if alnnx_result.ram and alnnx_result.ram.id:
        print(f"  Expected: ID 3289 - Kingston HyperX 16 GB")
        print(f"  Got: ID {alnnx_result.ram.id} - {alnnx_result.ram.name}")
        print(f"  Status: {'PASS' if alnnx_result.ram.id == 3289 else 'FAIL'}")

    print()
    print("=" * 70)
    print("Test 4: alnnx - Motherboard should be ID 7446 Asus TUF B450-PLUS GAMING")
    print("=" * 70)
    print(f"Motherboard: {alnnx_result.motherboard.model if alnnx_result.motherboard else 'None'}")
    if alnnx_result.motherboard and alnnx_result.motherboard.id:
        print(f"  Expected: ID 7446 - Asus TUF B450-PLUS GAMING")
        print(f"  Got: ID {alnnx_result.motherboard.id} - {alnnx_result.motherboard.brand} {alnnx_result.motherboard.model}")
        print(f"  Status: {'PASS' if alnnx_result.motherboard.id == 7446 else 'FAIL'}")
