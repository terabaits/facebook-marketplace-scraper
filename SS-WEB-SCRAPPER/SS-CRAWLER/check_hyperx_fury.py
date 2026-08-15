# -*- coding: utf-8 -*-
"""Check HyperX Fury RAMs in database."""
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
    
    print("=== HyperX Fury 16GB DDR4 RAMs ===")
    for ram in rams:
        if 'hyperx' in ram.name.lower() and 'fury' in ram.name.lower():
            if ram.capacity_gb == 16:
                speed_str = ram.speed or 'N/A'
                print(f"ID {ram.id}: {ram.name}")
                print(f"  Speed: {speed_str}")
                print(f"  Normalized: {ram.normalized_name}")
                print()
