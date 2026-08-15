# -*- coding: utf-8 -*-
"""Full debug of monitor matching."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
from sqlalchemy import text
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

# Load monitor references
with db.get_session() as session:
    result = session.execute(text("SELECT * FROM monitor_models"))
    monitors = [dict(row._mapping) for row in result]

print(f"Loaded {len(monitors)} monitors")

# Test listing
listing_text = """Sveiki, pārdodu labu, ātru un jaudīgu datoru. Dators izmantots 2 gadus - gan darbam, gan spēlēm. Nav ne reizi "crashojis". Strādāja ļoti labi un bez problēmām, mierīgi pavelk dažāda satura spēles. Pārdodu, jo tik bieži vairs nesanāk būt mājās, kā arī nevēlos, lai krāj putekļus ;) Komponentes: CPU - AMD R5 1600 3.2 GHz GPU - NVIDIA GeForce GTX 1060 6GB RAM - 2 x 4GB Viper Steel gaming DDR4 3200Mhz MB - B450 Aorus Elite PSU - 500W EcoSeries Storage - Crucial BX500 SAT 6gb/s 480GB SSD Cooling - 5 RF120M RGB Fans Un komplektā nāk vēl: Monitors - UltraGear 24GN600 144Hz 1ms (ideālā stāvoklī bez švīkām vai darbības traucējumiem) Klaviatūra - Royal Kludge RK84 red switch Par vairāk jautājumiem droši rakstat. Procesors: Amd r5 1600 Procesora frekvence, Ghz: 3.20 Pamat plate: B450 aorus elite Video: Nvidia gtx 1060 Operatīvā atmiņa, Gb: 8 HDD apjoms, Gb: 480 DVD: - Stāvoklis: lietota Cena: 365 €"""

normalized = normalize_text(listing_text)

# Manual check of model_base matching
print("=== Manual check of model_base matching ===")
monitor_29860 = next((m for m in monitors if m['id'] == 29860), None)
if monitor_29860:
    model = monitor_29860['model']
    model_lower = model.lower()
    model_clean = normalize_text(model)
    
    print(f"Monitor model: {model}")
    print(f"Normalized: {model_clean}")
    
    # Apply the base_model logic from the code
    base_model = re.sub(r'[a-z]+$', '', model_clean)
    print(f"Base model: {base_model}")
    
    # Get monitor context manually
    text_lower = listing_text.lower()
    monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays', 'screen', 'ultragear', '144hz']
    monitor_context_parts = []
    
    for kw in monitor_keywords:
        if kw in text_lower:
            kw_pos = text_lower.find(kw)
            start = max(0, kw_pos - 200)
            end = min(len(text_lower), kw_pos + len(kw) + 200)
            monitor_context_parts.append(text_lower[start:end])
            break
    
    monitor_context = ' '.join(monitor_context_parts)
    print(f"Monitor context length: {len(monitor_context)}")
    print(f"Monitor context: {monitor_context[:300]}...")
    
    print(f"\nBase model in context: {base_model in monitor_context}")
    print(f"24gn600 in context: {'24gn600' in monitor_context}")
    print(f"24gn600b in context: {'24gn600b' in monitor_context}")
    
    # Check the condition
    if base_model and len(base_model) >= 5 and base_model in monitor_context:
        print("\n✓ Would match model_base!")
    else:
        print(f"\n✗ Would NOT match model_base:")
        print(f"  base_model exists: {bool(base_model)}")
        print(f"  len(base_model) >= 5: {len(base_model) >= 5 if base_model else False}")
        print(f"  base_model in monitor_context: {base_model in monitor_context if base_model else False}")

# Now run the full match
print("\n=== Full match result ===")
# Convert dict monitors to MonitorReference objects
from src.models.schemas import MonitorReference
monitor_refs = []
for m in monitors:
    try:
        ref = MonitorReference(
            id=m['id'],
            brand=m['brand'],
            model=m['model'],
            size=m['size'],
            resolution=m['resolution'],
            refresh_rate=m['refresh_rate'],
            panel_type=m['panel_type'],
            search_keywords=m.get('search_keywords', []),
            normalized_name=m.get('normalized_name', '')
        )
        monitor_refs.append(ref)
    except:
        pass

print(f"Created {len(monitor_refs)} MonitorReference objects")

# Create proper matcher
proper_matcher = ComputerMonitorMatcher(monitor_refs)

result = proper_matcher.match_listing(listing_text, "")
if result[0]:
    print(f"Matched: {result[0].brand} {result[0].model}")
    print(f"  ID: {result[0].id}")
    print(f"  Confidence: {result[1]}")
    print(f"  Method: {result[2]}")
else:
    print("No monitor matched")
    print(f"  Confidence: {result[1]}")
    print(f"  Method: {result[2]}")
