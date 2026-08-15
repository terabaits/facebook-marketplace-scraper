import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text
import re

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

# Test text
text = """Pārdodu jaudīgu un svaigu gaming pc. Visas detaļas, izņemot videokarti ir 3 mēnešus vecas.

Specifikācijas:

RTX 3070 PNY

I5-12400F

16gb ram ddr4 3200mhz

256GB nvme ssd

700w psu"""

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"Text: {text_lower}\n")

ssd_capacity = 256
ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata', 'sandisk', 'seagate', 'teamgroup', 'pny']

for ssd in ssds:
    if ssd.id != 1381:  # Only check CS1030
        continue
    
    if ssd.capacity_gb:
        tolerance = min(max(ssd_capacity * 0.1, 20), 100)
        if abs(ssd.capacity_gb - ssd_capacity) > tolerance:
            continue
    else:
        continue
    
    ssd_brand = ssd.brand.lower() if ssd.brand else ""
    
    print(f"Checking SSD ID {ssd.id}: {ssd.brand} {ssd.model}")
    print(f"  Brand: '{ssd_brand}'")
    
    # Simulate the brand_near_ssd check
    brand_near_ssd = False
    ssd_context = text_lower
    for brand in ssd_brand_keywords:
        if brand in text_lower:
            brand_pos = text_lower.find(brand)
            segment = text_lower[brand_pos:brand_pos + 80]
            print(f"  Found '{brand}' at position {brand_pos}")
            print(f"    Segment: '{segment}'")
            has_kw = any(kw in segment for kw in ['ssd', 'nvme', 'm.2', 'hdd'])
            print(f"    Has SSD keywords: {has_kw}")
            if has_kw:
                ssd_context = segment
                brand_near_ssd = True
                break
    
    print(f"  brand_near_ssd: {brand_near_ssd}")
    
    # Check if brand in ssd_context
    brand_in_text = ssd_brand in ssd_context
    print(f"  Brand in ssd_context: {brand_in_text}")
    print(f"  ssd_context: '{ssd_context}'")
