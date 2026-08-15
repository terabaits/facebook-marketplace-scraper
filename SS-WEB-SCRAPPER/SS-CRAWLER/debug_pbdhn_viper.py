# -*- coding: utf-8 -*-
"""Debug pbdhn RAM matching."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.scraper.ram_matcher import RAMMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)

matcher = RAMMatcher(rams)

# pbdhn RAM text from listing
listing_text = """Sveiki, pārdodu labu, ātru un jaudīgu datoru. Dators izmantots 2 gadus - gan darbam, gan spēlēm. Nav ne reizi "crashojis". Strādāja ļoti labi un bez problēmām, mierīgi pavelk dažāda satura spēles. Pārdodu, jo tik bieži vairs nesanāk būt mājās, kā arī nevēlos, lai krāj putekļus ;) Komponentes: CPU - AMD R5 1600 3.2 GHz GPU - NVIDIA GeForce GTX 1060 6GB RAM - 2 x 4GB Viper Steel gaming DDR4 3200Mhz MB - B450 Aorus Elite PSU - 500W EcoSeries Storage - Crucial BX500 SAT 6gb/s 480GB SSD Cooling - 5 RF120M RGB Fans Un komplektā nāk vēl: Monitors - UltraGear 24GN600 144Hz 1ms (ideālā stāvoklī bez švīkām vai darbības traucējumiem) Klaviatūra - Royal Kludge RK84 red switch Par vairāk jautājumiem droši rakstat. Procesors: Amd r5 1600 Procesora frekvence, Ghz: 3.20 Pamat plate: B450 aorus elite Video: Nvidia gtx 1060 Operatīvā atmiņa, Gb: 8 HDD apjoms, Gb: 480 DVD: - Stāvoklis: lietota Cena: 365 €"""

normalized = normalize_text(listing_text)

print("=== pbdhn RAM Debug ===")
print(f"Normalized text contains 'viper': {'viper' in normalized}")
print(f"Normalized text contains 'steel': {'steel' in normalized}")
print(f"Normalized text contains 'patriot': {'patriot' in normalized}")

# Check RAM 783
ram_783 = next((r for r in rams if r.id == 783), None)
if ram_783:
    print(f"\n=== RAM 783 (Patriot Viper Steel 8GB) ===")
    print(f"  Name: {ram_783.name}")
    print(f"  Normalized: {ram_783.normalized_name}")
    print(f"  Keywords: {ram_783.search_keywords}")
    print(f"  Capacity: {ram_783.capacity_gb}")
    print(f"  Speed: {ram_783.speed}")
else:
    print("RAM 783 not found!")

# Check Crucial CT2K4G4DFS632A
ram_1996 = next((r for r in rams if r.id == 1996), None)
if ram_1996:
    print(f"\n=== RAM 1996 (Crucial) ===")
    print(f"  Name: {ram_1996.name}")
    print(f"  Normalized: {ram_1996.normalized_name}")
    print(f"  Keywords: {ram_1996.search_keywords}")
    print(f"  Capacity: {ram_1996.capacity_gb}")

# Extract RAM info
import re
ram_capacity = None
multi_patterns = [
    r'(\d+)\s*x\s*(\d+)\s*gb',
    r'(\d+)x\s*(\d+)\s*gb',
]
for pattern in multi_patterns:
    match = re.search(pattern, normalized)
    if match:
        sticks = int(match.group(1))
        per_stick = int(match.group(2))
        ram_capacity = sticks * per_stick
        print(f"\n  Multi-stick: {sticks} x {per_stick}GB = {ram_capacity}GB")
        break

if not ram_capacity:
    gb_match = re.search(r'(\d+)\s*gb', normalized)
    if gb_match:
        ram_capacity = int(gb_match.group(1))
        print(f"  Single capacity: {ram_capacity}GB")

# DDR type
ddr_match = re.search(r'ddr(\d+)', normalized)
ram_ddr = f"DDR{ddr_match.group(1)}" if ddr_match else None
print(f"  DDR type: {ram_ddr}")

# Frequency
freq_match = re.search(r'(\d{4})\s*mhz', normalized)
ram_freq = freq_match.group(1) if freq_match else None
print(f"  Frequency: {ram_freq}")

# Match RAM
print("\n=== RAM Matcher Result ===")
result = matcher.match_listing(listing_text, extracted_capacity=ram_capacity, 
                                extracted_ddr=ram_ddr, extracted_speed=ram_freq)
if result.ram:
    print(f"  Matched: ID {result.ram.id} - {result.ram.name}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
else:
    print("  No RAM matched!")

# Check viper steel specifically
print("\n=== Checking Viper Steel matches ===")
viper_steels = [r for r in rams if 'viper' in r.name.lower() and 'steel' in r.name.lower()]
for ram in viper_steels[:5]:
    print(f"  ID {ram.id}: {ram.name}")
