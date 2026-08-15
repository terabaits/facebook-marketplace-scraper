# -*- coding: utf-8 -*-
"""Check SSD IDs."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    # Check SSDs with "Green" or "545s"
    ssds = SSDReferenceRepository.get_all(session)
    
    print("=== SSDs with 'Green' ===")
    for ssd in ssds:
        if 'green' in ssd.model.lower():
            print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
            print(f"  Normalized: {ssd.normalized_name}")
            print(f"  Keywords: {ssd.search_keywords}")
            print()
    
    print("=== SSDs with '545' ===")
    for ssd in ssds:
        if '545' in ssd.model:
            print(f"ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")
            print(f"  Normalized: {ssd.normalized_name}")
            print(f"  Keywords: {ssd.search_keywords}")
            print()
