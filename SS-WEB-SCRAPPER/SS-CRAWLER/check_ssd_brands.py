# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

# Count by brand
brands = {}
for ssd in ssds:
    brand = ssd.brand.lower() if ssd.brand else "unknown"
    brands[brand] = brands.get(brand, 0) + 1

print("=== SSD Brands in Database ===")
for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True):
    print(f"  {brand}: {count}")

# Check for netac
print(f"\nIs 'netac' in brands? {'netac' in brands}")

# Check for Kingston NV2 specifically
print("\n=== Kingston SSDs ===")
for ssd in ssds:
    if ssd.brand and 'kingston' in ssd.brand.lower():
        print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} ({ssd.capacity_gb}GB)")
