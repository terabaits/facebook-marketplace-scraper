# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)
    
    print("=== SSDs with 'MX500' ===")
    for ssd in ssds:
        if 'mx500' in ssd.model.lower():
            print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
    
    print("\n=== SSDs with 'Crucial' and '500' ===")
    for ssd in ssds:
        if 'crucial' in ssd.brand.lower() and ('500' in ssd.model or ssd.capacity_gb == 500):
            print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
    
    print("\n=== All Crucial SSDs ===")
    count = 0
    for ssd in ssds:
        if 'crucial' in ssd.brand.lower():
            print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
            count += 1
            if count > 20:
                print("... (truncated)")
                break
