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

print(f"Loaded {len(ssds)} SSDs")

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

print(f"\nText: {text_lower}\n")

# Check what SSDs would match in the fallback
ssd_capacity = 256
ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata', 'sandisk', 'seagate', 'teamgroup']

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
    model_lower = ssd.model.lower() if ssd.model else ""
    
    print(f"Checking SSD ID {ssd.id}: {ssd.brand} {ssd.model}")
    print(f"  Brand: '{ssd_brand}'")
    print(f"  Model: '{model_lower}'")
    
    # Check if brand is in text
    brand_in_text = ssd_brand in text_lower
    print(f"  Brand in text: {brand_in_text}")
    
    # Check ssd_context
    ssd_context = text_lower
    for brand in ssd_brand_keywords:
        if brand in text_lower:
            brand_pos = text_lower.find(brand)
            segment = text_lower[brand_pos:brand_pos + 80]
            if any(kw in segment for kw in ['ssd', 'nvme', 'm.2', 'hdd']):
                ssd_context = segment
                print(f"  Found brand '{brand}' in SSD context: '{segment}'")
                break
    
    # Check if brand is in ssd_context
    brand_in_ssd_context = ssd_brand in ssd_context
    print(f"  Brand in SSD context: {brand_in_ssd_context}")
    print(f"  SSD context: '{ssd_context}'")
