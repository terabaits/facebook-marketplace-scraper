# -*- coding: utf-8 -*-
"""Check PSU and SSD IDs."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import PSURepository, SSDReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("=== PSU Checks ===")
    for psu_id in [6216, 6686]:
        psu = PSURepository.get_by_id(session, psu_id)
        if psu:
            print(f"\nPSU ID {psu_id}: {psu.name}")
            print(f"  Brand: {psu.brand}")
            print(f"  Wattage: {psu.wattage}")
            print(f"  Normalized: {psu.normalized_name}")
        else:
            print(f"\nPSU ID {psu_id}: NOT FOUND")
    
    print("\n\n=== SSD Checks ===")
    for ssd_id in [2112, 769]:
        ssd = SSDReferenceRepository.get_by_id(session, ssd_id)
        if ssd:
            print(f"\nSSD ID {ssd_id}: {ssd.brand} {ssd.model}")
            print(f"  Capacity: {ssd.capacity_gb}GB")
            print(f"  Normalized: {ssd.normalized_name}")
        else:
            print(f"\nSSD ID {ssd_id}: NOT FOUND")
