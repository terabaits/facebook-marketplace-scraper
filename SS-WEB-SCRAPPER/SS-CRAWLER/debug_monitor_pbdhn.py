# -*- coding: utf-8 -*-
"""Debug monitor detection for pbdhn."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
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
print(f"\n=== Checking monitor 24GN600-B (ID 29860) ===")

# Check if monitor ID 29860 exists
monitor_29860 = next((m for m in monitors if m['id'] == 29860), None)
if monitor_29860:
    print(f"Found: {monitor_29860['brand']} {monitor_29860['model']}")
    print(f"  Size: {monitor_29860['size']}, Resolution: {monitor_29860['resolution']}, Refresh: {monitor_29860['refresh_rate']}")
else:
    print("Monitor ID 29860 not found!")
    # Search for similar LG monitors
    lg_monitors = [m for m in monitors if m['brand'].lower() == 'lg']
    print(f"\nFound {len(lg_monitors)} LG monitors")
    lg_24 = [m for m in lg_monitors if m['size'] and '24' in str(m['size'])]
    print(f"Found {len(lg_24)} LG 24\" monitors")
    for m in lg_24[:10]:
        print(f"  ID {m['id']}: {m['model']}")

# Check text for monitor mentions
print(f"\n=== Checking normalized text ===")
print(f"Contains 'ultragear': {'ultragear' in normalized}")
print(f"Contains '24gn600': {'24gn600' in normalized}")
print(f"Contains '24gn600-b': {'24gn600-b' in normalized}")
print(f"Contains 'monitor': {'monitor' in normalized}")
print(f"Contains 'monitors': {'monitors' in normalized}")
print(f"Contains '144hz': {'144hz' in normalized}")

# Now let's check the monitor matching logic manually
print(f"\n=== Manual check for monitor match ===")

# Check if "24gn600" appears in any monitor model
found_24gn = []
for m in monitors:
    if '24gn' in m['model'].lower():
        found_24gn.append(m)
        
print(f"Found {len(found_24gn)} monitors with '24gn' in model:")
for m in found_24gn[:10]:
    print(f"  ID {m['id']}: {m['brand']} {m['model']}")

# Check normalized monitor models
if monitor_29860:
    model_norm = monitor_29860['normalized_name']
    print(f"\nMonitor 29860 normalized model: {model_norm}")
    print(f"Normalized text contains model: {model_norm in normalized}")

# The issue: "24GN600" vs "24GN600-B" - let's check if we need to handle model variants
print(f"\n=== Model variant analysis ===")
# Extract "24gn600" from text
gn600_match = re.search(r'24gn\d+', normalized)
if gn600_match:
    print(f"Found model pattern in text: {gn600_match.group()}")
    
    # Find monitors that match this pattern
    for m in found_24gn[:5]:
        model_lower = m['model'].lower()
        text_has = gn600_match.group() in model_lower
        print(f"  ID {m['id']}: {m['model']} - text pattern in model: {text_has}")
