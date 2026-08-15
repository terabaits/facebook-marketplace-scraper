# -*- coding: utf-8 -*-
"""Analyze the three new listing issues."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository, GPURepository, RAMReferenceRepository, SSDReferenceRepository, MotherboardRepository, PSUReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("=" * 70)
    print("Issue 1: fgfbp - CPU i5-14400F vs i5-14400")
    print("=" * 70)
    cpus = CPURepository.get_all(session)
    for cpu in cpus:
        if '14400' in cpu.cpu_name.lower():
            print(f"ID {cpu.id}: {cpu.cpu_name} (proc#: {cpu.processor_number})")
    
    print("\n" + "=" * 70)
    print("Issue 1: fgfbp - RAM ID 3319 (G.Skill F4-3200C16D-32GTZ)")
    print("=" * 70)
    rams = RAMReferenceRepository.get_all(session)
    for ram in rams:
        if ram.id == 3319 or '3200c16d' in ram.name.lower() or '32gtz' in ram.name.lower():
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Keywords: {ram.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 1: fgfbp - PSU ID 8593")
    print("=" * 70)
    psus = PSUReferenceRepository.get_all(session)
    for psu in psus:
        if psu.id == 8593:
            print(f"ID {psu.id}: {psu.name}")
            print(f"  Keywords: {psu.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 2: lphjf - GPU ID 315 (Radeon RX 6800 XT)")
    print("=" * 70)
    gpus = GPURepository.get_all(session)
    for gpu in gpus:
        if gpu.id == 315 or '6800' in gpu.model:
            print(f"ID {gpu.id}: {gpu.model}")
            print(f"  Keywords: {gpu.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 2: lphjf - SSD ID 859 (Kingston NV2)")
    print("=" * 70)
    ssds = SSDReferenceRepository.get_all(session)
    for ssd in ssds:
        if ssd.id == 859 or 'nv2' in ssd.model.lower():
            print(f"ID {ssd.id}: {ssd.model}")
            print(f"  Keywords: {ssd.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 2: lphjf - Motherboard ID 7008 (MSI MAG B650 TOMAHAWK WIFI)")
    print("=" * 70)
    mobos = MotherboardRepository.get_all(session)
    for mobo in mobos:
        if mobo.id == 7008 or ('tomahawk' in mobo.model.lower() and 'b650' in mobo.model.lower()):
            print(f"ID {mobo.id}: {mobo.brand} {mobo.model}")
            print(f"  Keywords: {mobo.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 3: aacph - RAM ID 1979 (G.Skill Aegis)")
    print("=" * 70)
    for ram in rams:
        if ram.id == 1979 or 'aegis' in ram.name.lower():
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Keywords: {ram.search_keywords}")
    
    print("\n" + "=" * 70)
    print("Issue 3: aacph - Motherboard ID 8231 (Gigabyte H310M S2H 2.0)")
    print("=" * 70)
    for mobo in mobos:
        if mobo.id == 8231 or ('h310m' in mobo.model.lower() and 's2h' in mobo.model.lower()):
            print(f"ID {mobo.id}: {mobo.brand} {mobo.model}")
            print(f"  Keywords: {mobo.search_keywords}")

print("\nAnalysis complete!")
