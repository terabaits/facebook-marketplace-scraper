# -*- coding: utf-8 -*-
"""Comprehensive test of all fixes."""
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
    print("TEST SUITE - All Fixed Issues")
    print("=" * 70)
    
    # Test 1: fcddo - CPU i5-4460 vs i5-4460S
    print("\n1. fcddo - CPU should be i5-4460 (not i5-4460S)")
    text1 = "pardod datoru procesors intel core i54460"
    result1 = matcher.match_listing(title="Test", description=text1, price=170)
    cpu1 = result1.cpu.cpu.cpu_name if result1.cpu else "None"
    status1 = "PASS" if "i5-4460" in cpu1 and "4460s" not in cpu1.lower() else "FAIL"
    print(f"   Got: {cpu1} - {status1}")
    
    # Test 2: alnnx - Motherboard TUF B450-PLUS GAMING
    print("\n2. alnnx - Motherboard should be TUF B450-PLUS GAMING (ID 7446)")
    text2 = "pardod datoru matesplate asus tuf b450plus gaming"
    result2 = matcher.match_listing(title="Test", description=text2, price=230)
    mb2 = result2.motherboard
    status2 = "PASS" if mb2 and mb2.id == 7446 else "FAIL"
    print(f"   Got: {mb2.model if mb2 else 'None'} (ID: {mb2.id if mb2 else 'N/A'}) - {status2}")
    
    # Test 3: alnnx - RAM Kingston HyperX
    print("\n3. alnnx - RAM should be Kingston HyperX (ID 3289)")
    text3 = "pardod datoru operativa atmina hyperx fury ddr4 16gb 3200mhz"
    result3 = matcher.match_listing(title="Test", description=text3, price=230)
    ram3 = result3.ram
    status3 = "PASS" if ram3 and "hyperx" in ram3.name.lower() else "FAIL"
    print(f"   Got: {ram3.name if ram3 else 'None'} (ID: {ram3.id if ram3 and ram3.id else 'N/A'}) - {status3}")
    
    # Test 4: kbdee - SSD Kingston A2000
    print("\n4. kbdee - SSD should be Kingston A2000 (ID 817)")
    text4 = "pardod datoru cietie diski ssd m2 1tb kingston nvme a2000"
    result4 = matcher.match_listing(title="Test", description=text4, price=1499)
    ssd4 = result4.ssd
    status4 = "PASS" if ssd4 and ssd4.id == 817 else "FAIL"
    print(f"   Got: {ssd4.name if ssd4 else 'None'} (ID: {ssd4.id if ssd4 else 'N/A'}) - {status4}")
    
    # Test 5: fgfbp - CPU i5-14400F (should now detect F suffix)
    print("\n5. fgfbp - CPU should be i5-14400F (has F suffix)")
    text5 = "pardod datoru procesors intel core i514400f"
    result5 = matcher.match_listing(title="Test", description=text5, price=1300)
    cpu5 = result5.cpu.cpu.cpu_name if result5.cpu else "None"
    status5 = "PASS" if "14400f" in cpu5.lower() else "FAIL"
    print(f"   Got: {cpu5} - {status5}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    results = [status1, status2, status3, status4, status5]
    passed = results.count("PASS")
    print(f"Passed: {passed}/{len(results)}")

print("\nDone!")
