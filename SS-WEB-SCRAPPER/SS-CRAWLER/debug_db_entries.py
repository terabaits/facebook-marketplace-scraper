# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository, SSDReferenceRepository, MonitorRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    print("=== RAM ID 783 (Patriot Viper Steel 8GB) ===")
    ram = RAMReferenceRepository.get_by_id(session, 783)
    if ram:
        print(f"  Name: {ram.name}")
        print(f"  Brand: {ram.brand}")
        print(f"  Capacity: {ram.capacity_gb}")
        print(f"  Normalized: {ram.normalized_name}")
        print(f"  Keywords: {ram.search_keywords[:5]}")
    else:
        print("  Not found")
    
    print("\n=== SSD ID 449 (Crucial) ===")
    ssd = SSDReferenceRepository.get_by_id(session, 449)
    if ssd:
        print(f"  Brand: {ssd.brand}")
        print(f"  Model: {ssd.model}")
        print(f"  Capacity: {ssd.capacity_gb}")
        print(f"  Normalized: {ssd.normalized_name}")
    else:
        print("  Not found")
    
    print("\n=== SSD ID 587 ===")
    ssd = SSDReferenceRepository.get_by_id(session, 587)
    if ssd:
        print(f"  Brand: {ssd.brand}")
        print(f"  Model: {ssd.model}")
        print(f"  Capacity: {ssd.capacity_gb}")
        print(f"  Normalized: {ssd.normalized_name}")
    else:
        print("  Not found")
    
    print("\n=== Monitor ID 29860 (LG 24GN600-B) ===")
    mon = MonitorRepository.get_by_id(session, 29860)
    if mon:
        print(f"  Brand: {mon.brand}")
        print(f"  Model: {mon.model}")
        print(f"  Size: {mon.size}")
        print(f"  Normalized: {mon.normalized_name}")
    else:
        print("  Not found")
    
    # Find LG monitors with 24
    print("\n=== LG Monitors with 24 ===")
    monitors = MonitorRepository.get_all(session)
    for m in monitors:
        if m.brand and 'lg' in m.brand.lower() and m.size and '24' in str(m.size):
            print(f"  ID {m.id}: {m.brand} {m.model} ({m.size}\")")
