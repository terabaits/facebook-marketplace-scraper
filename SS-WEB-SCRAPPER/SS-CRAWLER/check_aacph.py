# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository, MotherboardRepository, MonitorRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    # Check RAM ID 1979 - G.Skill Aegis 32 GB
    ram = RAMReferenceRepository.get_by_id(session, 1979)
    if ram:
        print(f"RAM 1979: {ram.name}")
        print(f"  Brand: {ram.name.split()[0] if ram.name else 'N/A'}")
        print(f"  Capacity: {ram.capacity_gb}GB")
        print(f"  Speed: {ram.speed}")
        print(f"  Keywords: {ram.search_keywords}")
        print(f"  Normalized: {normalize_text(ram.name)}")
    else:
        print("RAM 1979 not found")
    
    # Check Motherboard ID 8231 - Gigabyte H310M S2H 2.0
    mb = MotherboardRepository.get_by_id(session, 8231)
    if mb:
        print(f"\nMotherboard 8231: {mb.brand} {mb.model}")
        print(f"  Chipset: {mb.chipset}")
        print(f"  Socket: {mb.socket}")
        print(f"  Keywords: {mb.search_keywords}")
        print(f"  Normalized: {normalize_text(f'{mb.brand} {mb.model}')}")
    else:
        print("Motherboard 8231 not found")
    
    # Check Monitor for AOC 2590G4
    all_monitors = MonitorRepository.get_all(session)
    aoc_monitors = [m for m in all_monitors if 'aoc' in m.brand.lower()]
    print(f"\nAOC Monitors found: {len(aoc_monitors)}")
    for m in aoc_monitors[:10]:  # Show first 10
        print(f"  ID {m.id}: {m.brand} {m.model} - Size: {m.size}")
        print(f"    Keywords: {m.search_keywords}")
        print(f"    Normalized: {normalize_text(f'{m.brand} {m.model}')}")
    
    # Check all monitors with 2590 in model
    monitors_2590 = [m for m in all_monitors if '2590' in m.model.lower()]
    print(f"\nMonitors with '2590' in model: {len(monitors_2590)}")
    for m in monitors_2590:
        print(f"  ID {m.id}: {m.brand} {m.model} - Size: {m.size}")
