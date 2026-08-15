# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository, RAMReferenceRepository, PSUReferenceRepository
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cpus = CPURepository.get_all(session)
    rams = RAMReferenceRepository.get_all(session)
    psus = PSUReferenceRepository.get_all(session)
    
    cpu_matcher = CPUMatcher(cpus)
    ram_matcher = RAMMatcher(rams)
    psu_matcher = PSUMatcher(psus)

    print("=== fgfbp Debug ===")
    text = """Pārdod datoru. Procesors: Intel Core i5-14400F, Mātesplate: Asus PRIME Z790-P, 
Operatīvā atmiņa: G.Skill F4-3200C16D-32GTZ 32 GB, Cietie diski: SSD 1TB, 
Video karte: Radeon RX 9060 XT, Barošanas bloks: 750W"""
    
    normalized = normalize_text(text)
    print(f"Normalized: {normalized}\n")
    
    # Check CPU
    print("=== CPU Check ===")
    print("Looking for i5-14400F vs i5-14400...")
    for cpu in cpus:
        if '14400' in cpu.cpu_name:
            print(f"ID {cpu.id}: {cpu.cpu_name}")
    
    cpu_result = cpu_matcher.match(text)
    print(f"\nMatched CPU: {cpu_result.cpu.cpu_name if cpu_result.cpu else 'None'} (ID: {cpu_result.cpu.id if cpu_result.cpu else 'N/A'})")
    
    # Check RAM
    print("\n=== RAM Check ===")
    print("Looking for G.Skill F4-3200C16D-32GTZ...")
    for ram in rams:
        if 'f4-3200c16d' in ram.name.lower() or '32gtz' in ram.name.lower():
            print(f"ID {ram.id}: {ram.name}")
    
    ram_result = ram_matcher.match_listing(text, extracted_capacity=32, extracted_ddr="DDR4")
    print(f"\nMatched RAM: {ram_result.ram.name if ram_result.ram else 'None'} (ID: {ram_result.ram.id if ram_result.ram else 'N/A'})")
    
    # Check PSU
    print("\n=== PSU Check ===")
    print("Looking for PSU ID 8593...")
    for psu in psus:
        if psu.id == 8593:
            print(f"ID {psu.id}: {psu.name}")
    
    psu_result = psu_matcher.match_listing(text, extracted_wattage=750)
    print(f"\nMatched PSU: {psu_result.psu.name if psu_result.psu else 'None'} (ID: {psu_result.psu.id if psu_result.psu else 'N/A'})")
