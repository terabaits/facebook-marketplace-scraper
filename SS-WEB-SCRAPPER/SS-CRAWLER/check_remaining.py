# -*- coding: utf-8 -*-
"""Check the remaining items that need fixing."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("=" * 70)
    print("1. fgfbp RAM - ID 3319 (G.Skill F4-3200C16D-32GTZ)")
    print("=" * 70)
    rams = RAMReferenceRepository.get_all(session)
    for ram in rams:
        if ram.id == 3319:
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Normalized: {ram.normalized_name}")
            print(f"  Keywords: {ram.search_keywords}")
            print(f"  Capacity: {ram.capacity_gb} GB")
            print(f"  Speed: {ram.speed}")
    
    print("\n" + "=" * 70)
    print("2. fgfbp PSU - ID 8593")
    print("=" * 70)
    psus = PSUReferenceRepository.get_all(session)
    for psu in psus:
        if psu.id == 8593:
            print(f"ID {psu.id}: {psu.name}")
            print(f"  Wattage: {psu.wattage}")
            print(f"  Keywords: {psu.search_keywords}")
    
    print("\n" + "=" * 70)
    print("3. lphjf Motherboard - ID 7008 (MSI MAG B650 TOMAHAWK WIFI)")
    print("=" * 70)
    mobos = MotherboardRepository.get_all(session)
    for mobo in mobos:
        if mobo.id == 7008:
            print(f"ID {mobo.id}: {mobo.brand} {mobo.model}")
            print(f"  Keywords: {mobo.search_keywords}")
    
    print("\n" + "=" * 70)
    print("4. aacph RAM - ID 1979 (G.Skill Aegis)")
    print("=" * 70)
    for ram in rams:
        if ram.id == 1979:
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Normalized: {ram.normalized_name}")
            print(f"  Keywords: {ram.search_keywords}")
    
    print("\n" + "=" * 70)
    print("5. aacph Motherboard - ID 8231 (Gigabyte H310M S2H 2.0)")
    print("=" * 70)
    for mobo in mobos:
        if mobo.id == 8231:
            print(f"ID {mobo.id}: {mobo.brand} {mobo.model}")
            print(f"  Keywords: {mobo.search_keywords}")
