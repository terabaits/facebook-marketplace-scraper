# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')

from src.database.connection import get_db_manager, init_database
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.config import AppConfig
from src.utils.text import normalize_text
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    matcher = ComputerMatcher(session)

    # Listing 1: fgfbp
    print("="*70)
    print("Listing 1: fgfbp")
    print("Expected: CPU i5-14400F, RAM ID 3319, PSU ID 8593")
    print("="*70)
    fgfbp_text = """Pārdod datoru. Procesors: Intel Core i5-14400F, Mātesplate: Asus PRIME Z790-P, 
Operatīvā atmiņa: G.Skill F4-3200C16D-32GTZ 32 GB, Cietie diski: SSD 1TB, 
Video karte: Radeon RX 9060 XT, Barošanas bloks: 750W"""
    
    fgfbp = matcher.match_listing(title="Pārdod datoru", description=fgfbp_text, price=1300)
    print(f"CPU: {fgfbp.cpu.cpu.cpu_name if fgfbp.cpu else 'None'} (Expected: i5-14400F)")
    if fgfbp.cpu:
        has_f = '14400f' in fgfbp.cpu.cpu.cpu_name.lower()
        print(f"  Has F suffix: {has_f}")
    print(f"RAM: {fgfbp.ram.name if fgfbp.ram else 'None'} (Expected: ID 3319)")
    if fgfbp.ram and fgfbp.ram.id:
        print(f"  RAM ID: {fgfbp.ram.id}")
    print(f"PSU: {fgfbp.psu.name if fgfbp.psu else 'None'} (Expected: ID 8593)")
    if fgfbp.psu and fgfbp.psu.id:
        print(f"  PSU ID: {fgfbp.psu.id}")

    # Listing 2: lphjf
    print()
    print("="*70)
    print("Listing 2: lphjf")
    print("Expected: GPU ID 315 (RX 6800 XT), SSD ID 859 (Kingston NV2), MB ID 7008")
    print("="*70)
    lphjf_text = """Pārdod datoru. Procesors: AMD Ryzen 7 8700F, Mātesplate: MSI MAG B650 TOMAHAWK WIFI,
Operatīvā atmiņa: DDR5 32GB, Cietie diski: SSD M.2 2TB Kingston NV2,
Video karte: Powercolor red devil RX6800XT 16gb, Barošanas bloks: 1200W"""
    
    lphjf = matcher.match_listing(title="Pārdod datoru", description=lphjf_text, price=1199)
    print(f"GPU: {lphjf.gpu.name if lphjf.gpu else 'None'} (Expected: ID 315 RX 6800 XT)")
    if lphjf.gpu:
        print(f"  GPU ID: {lphjf.gpu.id}")
    print(f"SSD: {lphjf.ssd.name if lphjf.ssd else 'None'} (Expected: ID 859 Kingston NV2)")
    if lphjf.ssd and lphjf.ssd.id:
        print(f"  SSD ID: {lphjf.ssd.id}")
    print(f"Motherboard: {lphjf.motherboard.model if lphjf.motherboard else 'None'} (Expected: ID 7008)")
    if lphjf.motherboard:
        print(f"  MB ID: {lphjf.motherboard.id}")

    # Listing 3: aacph
    print()
    print("="*70)
    print("Listing 3: aacph")
    print("Expected: RAM ID 1979, MB ID 8231, Monitor AOC 2590G4")
    print("="*70)
    aacph_text = """Pārdod datoru. Procesors: Intel Core i5-9400F, Mātesplate: Gigabyte H310M S2H 2.0,
Operatīvā atmiņa: G.Skill Aegis 32GB DDR4, Cietie diski: SSD 512GB,
Video karte: GTX 1660, Monitors: AOC 25 LCD 2590G4"""
    
    aacph = matcher.match_listing(title="Pārdod datoru", description=aacph_text, price=550)
    print(f"RAM: {aacph.ram.name if aacph.ram else 'None'} (Expected: ID 1979 G.Skill Aegis)")
    if aacph.ram and aacph.ram.id:
        print(f"  RAM ID: {aacph.ram.id}")
    print(f"Motherboard: {aacph.motherboard.model if aacph.motherboard else 'None'} (Expected: ID 8231)")
    if aacph.motherboard:
        print(f"  MB ID: {aacph.motherboard.id}")
    print(f"Monitor: {aacph.monitor.model if aacph.monitor else 'None'} (Expected: AOC 2590G4)")
    if aacph.monitor:
        print(f"  Monitor ID: {aacph.monitor.id}")
