# -*- coding: utf-8 -*-
"""Verify all fixes are working."""
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
    matcher = ComputerMatcher(session)

    print("=" * 70)
    print("Test 1: fcddo - CPU should be i5-4460 (not i5-4460S)")
    print("=" * 70)
    fcddo = matcher.match_listing(
        title="Pārdod datoru",
        description="Procesors: Intel Core i5-4460, Mātesplate: MSI H81M Eco, Operatīvā atmiņa: DDR3 16GB",
        price=170
    )
    if fcddo.cpu:
        expected = "i5-4460" in fcddo.cpu.cpu.cpu_name and "4460s" not in fcddo.cpu.cpu.cpu_name.lower()
        print(f"Got: {fcddo.cpu.cpu.cpu_name}")
        print(f"Status: {'PASS' if expected else 'FAIL'}")

    print()
    print("=" * 70)
    print("Test 2: alnnx - Motherboard ID 7446 (TUF B450-PLUS GAMING)")
    print("=" * 70)
    alnnx = matcher.match_listing(
        title="Pārdod spēļu datoru",
        description="Procesors: AMD Ryzen 5 1600X, Mātesplate: Asus TUF B450-PLUS GAMING, Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz",
        price=230
    )
    if alnnx.motherboard:
        expected = alnnx.motherboard.id == 7446
        print(f"Got: ID {alnnx.motherboard.id} - {alnnx.motherboard.brand} {alnnx.motherboard.model}")
        print(f"Status: {'PASS' if expected else 'FAIL'}")

    print()
    print("=" * 70)
    print("Test 3: alnnx - RAM should be Kingston HyperX (ID 3289)")
    print("=" * 70)
    if alnnx.ram and alnnx.ram.id:
        expected = alnnx.ram.id == 3289
        print(f"Got: ID {alnnx.ram.id} - {alnnx.ram.name}")
        print(f"Status: {'PASS' if expected else 'FAIL'}")
    else:
        print(f"Got: {alnnx.ram.name if alnnx.ram else 'None'} (no ID)")
        print("Status: FAIL")

    print()
    print("=" * 70)
    print("Test 4: kbdee - SSD ID 817 (Kingston A2000)")
    print("=" * 70)
    kbdee = matcher.match_listing(
        title="Pārdod jaunu datoru",
        description="Procesors: Intel Core i7-14700KF, Cietie diski: SSD M.2 1TB Kingston NVMe A2000",
        price=1499
    )
    if kbdee.ssd and kbdee.ssd.id:
        expected = kbdee.ssd.id == 817
        print(f"Got: ID {kbdee.ssd.id} - {kbdee.ssd.name}")
        print(f"Status: {'PASS' if expected else 'FAIL'}")
    else:
        print(f"Got: {kbdee.ssd.name if kbdee.ssd else 'None'} (no ID)")
        print("Status: FAIL")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
