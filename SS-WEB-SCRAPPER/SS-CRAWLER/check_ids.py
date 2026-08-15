#!/usr/bin/env python3
"""Check specific IDs in database."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository, RAMReferenceRepository, PSURepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    # Check CPU i5-14400F
    print("=== CPUs with 14400 ===")
    cpus = CPUReferenceRepository.get_all(session)
    for cpu in cpus:
        if '14400' in cpu.cpu_name:
            print(f"ID {cpu.id}: {cpu.cpu_name} - {cpu.processor_number}")
    
    # Check RAM ID 3319
    print("\n=== RAM ID 3319 ===")
    rams = RAMReferenceRepository.get_all(session)
    for ram in rams:
        if ram.id == 3319:
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Capacity: {ram.capacity_gb}GB")
            print(f"  Speed: {ram.speed}")
            print(f"  Search keywords: {ram.search_keywords}")
    
    # Check if there's F4-3000C16D
    print("\n=== RAMs with F4-3000 ===")
    for ram in rams:
        if 'f4-3000' in ram.name.lower():
            print(f"ID {ram.id}: {ram.name}")
    
    # Check PSU ID 8593
    print("\n=== PSU ID 8593 ===")
    psus = PSURepository.get_all(session)
    for psu in psus:
        if psu.id == 8593:
            print(f"ID {psu.id}: {psu.name}")
            print(f"  Wattage: {psu.wattage}W")
            print(f"  Search keywords: {psu.search_keywords}")
    
    # Check XFX PSUs
    print("\n=== XFX PSUs ===")
    for psu in psus:
        if 'xfx' in psu.name.lower():
            print(f"ID {psu.id}: {psu.name} - {psu.wattage}W")
