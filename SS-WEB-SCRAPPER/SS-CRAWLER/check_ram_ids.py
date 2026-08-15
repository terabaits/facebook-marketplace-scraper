# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    
    # Check ID 110 and 3289
    for ram in rams:
        if ram.id in [110, 3289]:
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Capacity: {ram.capacity_gb} GB")
            print(f"  Speed: {ram.speed}")
            print(f"  Keywords: {ram.search_keywords}")
            print()
