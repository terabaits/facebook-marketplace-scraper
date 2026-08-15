# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

# Find all Netac SSDs and their brand keys
print("Netac SSDs in database:")
for ssd in ssds:
    if ssd.brand and 'netac' in ssd.brand.lower():
        brand_key = normalize_text(ssd.brand)
        print(f"  ID {ssd.id}: Original brand='{ssd.brand}' -> Key='{brand_key}'")
        print(f"    Model: {ssd.model}")
        print(f"    Capacity: {ssd.capacity_gb}")
