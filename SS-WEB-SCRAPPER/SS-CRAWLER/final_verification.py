# -*- coding: utf-8 -*-
"""Final verification of ALL fixes - comprehensive test."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

def test_all_fixes():
    with db.get_session() as session:
        matcher = ComputerMatcher(session)
        
        print("=" * 80)
        print("FINAL VERIFICATION - All Fixes")
        print("=" * 80)
        
        results = []
        
        # ===== ORIGINAL ISSUES =====
        
        # 1. fcddo - CPU i5-4460 (not i5-4460S)
        print("\n1. fcddo - CPU should be i5-4460 (NOT i5-4460S)")
        text = "pardod datoru procesors intel core i54460"
        result = matcher.match_listing(title="Test", description=text, price=170)
        cpu = result.cpu.cpu.cpu_name if result.cpu else "None"
        has_s = "4460s" in cpu.lower()
        status = "PASS" if "i5-4460" in cpu and not has_s else "FAIL"
        results.append(("fcddo CPU", status, cpu, "i5-4460", "i5-4460S" if has_s else ""))
        print(f"   Got: {cpu} (ID: {result.cpu.cpu.id if result.cpu else 'N/A'}) - {status}")
        
        # 2. alnnx - Motherboard TUF B450-PLUS GAMING (ID 7446)
        print("\n2. alnnx - Motherboard should be ID 7446 (TUF B450-PLUS GAMING)")
        text = "pardod datoru matesplate asus tuf b450plus gaming"
        result = matcher.match_listing(title="Test", description=text, price=230)
        mb = result.motherboard
        status = "PASS" if mb and mb.id == 7446 else "FAIL"
        results.append(("alnnx MB", status, mb.model if mb else "None", "ID 7446", ""))
        print(f"   Got: {mb.model if mb else 'None'} (ID: {mb.id if mb else 'N/A'}) - {status}")
        
        # 3. alnnx - RAM Kingston HyperX (ID 3289)
        print("\n3. alnnx - RAM should be Kingston HyperX")
        text = "pardod datoru operativa atmina hyperx fury ddr4 16gb 3200mhz"
        result = matcher.match_listing(title="Test", description=text, price=230)
        ram = result.ram
        status = "PASS" if ram and "hyperx" in ram.name.lower() else "FAIL"
        results.append(("alnnx RAM", status, ram.name if ram else "None", "HyperX", ""))
        print(f"   Got: {ram.name if ram else 'None'} (ID: {ram.id if ram and ram.id else 'N/A'}) - {status}")
        
        # 4. kbdee - SSD Kingston A2000 (ID 817)
        print("\n4. kbdee - SSD should be ID 817 (Kingston A2000)")
        text = "pardod datoru cietie diski ssd m2 1tb kingston nvme a2000"
        result = matcher.match_listing(title="Test", description=text, price=1499)
        ssd = result.ssd
        status = "PASS" if ssd and ssd.id == 817 else "FAIL"
        results.append(("kbdee SSD", status, ssd.name if ssd else "None", "ID 817", ""))
        print(f"   Got: {ssd.name if ssd else 'None'} (ID: {ssd.id if ssd else 'N/A'}) - {status}")
        
        # ===== NEW ISSUES =====
        
        # 5. fgfbp - CPU i5-14400F (has F suffix)
        print("\n5. fgfbp - CPU should be i5-14400F (has F suffix)")
        text = "pardod datoru procesors intel core i514400f"
        result = matcher.match_listing(title="Test", description=text, price=1300)
        cpu = result.cpu.cpu.cpu_name if result.cpu else "None"
        status = "PASS" if "14400f" in cpu.lower() else "FAIL"
        results.append(("fgfbp CPU", status, cpu, "i5-14400F", ""))
        print(f"   Got: {cpu} (ID: {result.cpu.cpu.id if result.cpu else 'N/A'}) - {status}")
        
        # 6. fgfbp - RAM G.Skill F4-3200C16D-32GTZ (ID 3319)
        print("\n6. fgfbp - RAM should be ID 3319 (G.Skill F4-3200C16D-32GTZ)")
        text = "pardod datoru operativa atmina gskill f43200c16d32gtz 32gb ddr4"
        result = matcher.match_listing(title="Test", description=text, price=1300)
        ram = result.ram
        status = "PASS" if ram and ram.id == 3319 else "FAIL"
        results.append(("fgfbp RAM", status, ram.name if ram else "None", "ID 3319", ""))
        print(f"   Got: {ram.name if ram else 'None'} (ID: {ram.id if ram and ram.id else 'N/A'}) - {status}")
        
        # 7. lphjf - GPU RX 6800 XT (ID 315)
        print("\n7. lphjf - GPU should be ID 315 (RX 6800 XT)")
        text = "pardod datoru video karte powercolor red devil rx6800xt 16gb"
        result = matcher.match_listing(title="Test", description=text, price=1199)
        gpu = result.gpu
        status = "PASS" if gpu and gpu.id == 315 else "FAIL"
        results.append(("lphjf GPU", status, gpu.name if gpu else "None", "ID 315", ""))
        print(f"   Got: {gpu.name if gpu else 'None'} (ID: {gpu.id if gpu else 'N/A'}) - {status}")
        
        # 8. lphjf - SSD Kingston NV2 (ID 859)
        print("\n8. lphjf - SSD should be ID 859 (Kingston NV2)")
        text = "pardod datoru cietie diski ssd m2 2tb kingston nv2"
        result = matcher.match_listing(title="Test", description=text, price=1199)
        ssd = result.ssd
        status = "PASS" if ssd and ssd.id == 859 else "FAIL"
        results.append(("lphjf SSD", status, ssd.name if ssd else "None", "ID 859", ""))
        print(f"   Got: {ssd.name if ssd else 'None'} (ID: {ssd.id if ssd else 'N/A'}) - {status}")
        
        # 9. lphjf - Motherboard MSI MAG B650 TOMAHAWK WIFI (ID 7008)
        print("\n9. lphjf - Motherboard should be ID 7008 (MSI MAG B650 TOMAHAWK WIFI)")
        text = "pardod datoru matesplate msi mag b650 tomahawk wifi"
        result = matcher.match_listing(title="Test", description=text, price=1199)
        mb = result.motherboard
        status = "PASS" if mb and mb.id == 7008 else "FAIL"
        results.append(("lphjf MB", status, mb.model if mb else "None", "ID 7008", ""))
        print(f"   Got: {mb.model if mb else 'None'} (ID: {mb.id if mb else 'N/A'}) - {status}")
        
        # 10. aacph - RAM G.Skill Aegis (ID 1979)
        print("\n10. aacph - RAM should be ID 1979 (G.Skill Aegis)")
        text = "pardod datoru operativa atmina gskill aegis 32gb ddr4"
        result = matcher.match_listing(title="Test", description=text, price=550)
        ram = result.ram
        status = "PASS" if ram and ram.id == 1979 else "FAIL"
        results.append(("aacph RAM", status, ram.name if ram else "None", "ID 1979", ""))
        print(f"   Got: {ram.name if ram else 'None'} (ID: {ram.id if ram and ram.id else 'N/A'}) - {status}")
        
        # 11. aacph - Motherboard Gigabyte H310M S2H 2.0 (ID 8231)
        print("\n11. aacph - Motherboard should be ID 8231 (Gigabyte H310M S2H 2.0)")
        text = "pardod datoru matesplate gigabyte h310m s2h 2.0"
        result = matcher.match_listing(title="Test", description=text, price=550)
        mb = result.motherboard
        status = "PASS" if mb and mb.id == 8231 else "FAIL"
        results.append(("aacph MB", status, mb.model if mb else "None", "ID 8231", ""))
        print(f"   Got: {mb.model if mb else 'None'} (ID: {mb.id if mb else 'N/A'}) - {status}")
        
        # Summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        passed = sum(1 for _, status, _, _, _ in results if status == "PASS")
        failed = sum(1 for _, status, _, _, _ in results if status == "FAIL")
        print(f"\nTotal Tests: {len(results)}")
        print(f"PASSED: {passed}")
        print(f"FAILED: {failed}")
        print(f"\nSuccess Rate: {passed}/{len(results)} ({100*passed//len(results)}%)")
        
        if failed > 0:
            print("\n" + "=" * 80)
            print("FAILED TESTS:")
            print("=" * 80)
            for name, status, got, expected, _ in results:
                if status == "FAIL":
                    print(f"  - {name}: Expected '{expected}', Got '{got}'")
        
        return passed == len(results)

if __name__ == "__main__":
    success = test_all_fixes()
    sys.exit(0 if success else 1)
