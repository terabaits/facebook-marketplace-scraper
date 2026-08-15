# -*- coding: utf-8 -*-
"""Check PSU IDs."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import PSURepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    psu = PSURepository.get_by_id(session, 6216)
    if psu:
        print(f"PSU ID 6216: {psu.name}")
        print(f"  Brand: {psu.brand}")
        print(f"  Wattage: {psu.wattage}")
        print(f"  Normalized: {psu.normalized_name}")
        print(f"  Keywords: {psu.search_keywords}")
    else:
        print("PSU ID 6216 not found")
    
    print()
    
    psu = PSURepository.get_by_id(session, 6686)
    if psu:
        print(f"PSU ID 6686: {psu.name}")
        print(f"  Brand: {psu.brand}")
        print(f"  Wattage: {psu.wattage}")
        print(f"  Normalized: {psu.normalized_name}")
        print(f"  Keywords: {psu.search_keywords}")
    else:
        print("PSU ID 6686 not found")
