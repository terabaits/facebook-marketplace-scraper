# -*- coding: utf-8 -*-
"""Comprehensive test of remaining fixes."""
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
    print("COMPREHENSIVE TEST - Remaining Issues")
    print("=" * 70)
    
    results = []
    
    # 1. fgfbp - CPU i5-14400F
    print("\n1. fgfbp - CPU should be i5-14400F (has F suffix)")
    text = "pardod datoru procesors intel core i514400f"
    result = matcher.match_listing(title="Test", description=text, price=1300)
    cpu = result.cpu.cpu.cpu_name if result.cpu else "None"
    status = "PASS" if "14400f" in cpu.lower() else "FAIL"
    results.append(("fgfbp CPU", status, cpu, "i5-14400F"))
    print(f"   Got: {cpu} - {status}")
    
    # 2. fgfbp - RAM ID 3319
    print("\n2. fgfbp - RAM should be ID 3319 (G.Skill F4-3200C16D-32GTZ)")
    text = "pardod datoru operativa atmina gskill f43200c16d32gtz 32gb ddr4"
    result = matcher.match_listing(title="Test", description=text, price=1300)
    ram = result.ram
    status = "PASS" if ram and ram.id == 3319 else "FAIL"
    results.append(("fgfbp RAM", status, ram.name if ram else "None", "ID 3319"))
    print(f"   Got: {ram.name if ram else 'None'} (ID: {ram.id if ram and ram.id else 'N/A'}) - {status}")
    
    # 3. lphjf - GPU RX 6800 XT
    print("\n3. lphjf - GPU should be RX 6800 XT (ID 315)")
    text = "pardod datoru video karte powercolor red devil rx6800xt 16gb"
    result = matcher.match_listing(title="Test", description=text, price=1199)
    gpu = result.gpu
    status = "PASS" if gpu and gpu.id == 315 else "FAIL"
    results.append(("lphjf GPU", status, gpu.name if gpu else "None", "ID 315"))
    print(f"   Got: {gpu.name if gpu else 'None'} (ID: {gpu.id if gpu else 'N/A'}) - {status}")
    
    # 4. lphjf - SSD Kingston NV2
    print("\n4. lphjf - SSD should be Kingston NV2 (ID 859)")
    text = "pardod datoru cietie diski ssd m2 2tb kingston nv2"
    result = matcher.match_listing(title="Test", description=text, price=1199)
    ssd = result.ssd
    status = "PASS" if ssd and ssd.id == 859 else "FAIL"
    results.append(("lphjf SSD", status, ssd.name if ssd else "None", "ID 859"))
    print(f"   Got: {ssd.name if ssd else 'None'} (ID: {ssd.id if ssd else 'N/A'}) - {status}")
    
    # 5. aacph - RAM G.Skill Aegis
    print("\n5. aacph - RAM should be G.Skill Aegis (ID 1979)")
    text = "pardod datoru operativa atmina gskill aegis 32gb ddr4"
    result = matcher.match_listing(title="Test", description=text, price=550)
    ram = result.ram
    status = "PASS" if ram and ram.id == 1979 else "FAIL"
    results.append(("aacph RAM", status, ram.name if ram else "None", "ID 1979"))
    print(f"   Got: {ram.name if ram else 'None'} (ID: {ram.id if ram and ram.id else 'N/A'}) - {status}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, status, _, _ in results if status == "PASS")
    print(f"Passed: {passed}/{len(results)}")
    print("\nDetails:")
    for name, status, got, expected in results:
        print(f"  {name}: {status} (got: {got}, expected: {expected})")

print("\nDone!")
