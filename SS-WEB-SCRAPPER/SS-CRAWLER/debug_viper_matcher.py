# -*- coding: utf-8 -*-
"""Debug Viper Steel matching in RAM matcher."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.scraper.ram_matcher import RAMMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
from rapidfuzz import fuzz
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

# Load RAM references
with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)

# Create RAM matcher
ram_matcher = RAMMatcher(rams)

# Test listing
listing_text = """Sveiki, pārdodu labu, ātru un jaudīgu datoru. Dators izmantots 2 gadus - gan darbam, gan spēlēm. Nav ne reizi "crashojis". Strādāja ļoti labi un bez problēmām, mierīgi pavelk dažāda satura spēles. Pārdodu, jo tik bieži vairs nesanāk būt mājās, kā arī nevēlos, lai krāj putekļus ;) Komponentes: CPU - AMD R5 1600 3.2 GHz GPU - NVIDIA GeForce GTX 1060 6GB RAM - 2 x 4GB Viper Steel gaming DDR4 3200Mhz MB - B450 Aorus Elite PSU - 500W EcoSeries Storage - Crucial BX500 SAT 6gb/s 480GB SSD Cooling - 5 RF120M RGB Fans Un komplektā nāk vēl: Monitors - UltraGear 24GN600 144Hz 1ms (ideālā stāvoklī bez švīkām vai darbības traucējumiem) Klaviatūra - Royal Kludge RK84 red switch Par vairāk jautājumiem droši rakstat. Procesors: Amd r5 1600 Procesora frekvence, Ghz: 3.20 Pamat plate: B450 aorus elite Video: Nvidia gtx 1060 Operatīvā atmiņa, Gb: 8 HDD apjoms, Gb: 480 DVD: - Stāvoklis: lietota Cena: 365 €"""

normalized = normalize_text(listing_text)
print(f"=== Checking candidate RAMs ===")

# Get RAM 783
viper_783 = next((r for r in rams if r.id == 783), None)
# Get RAM 1996
crucial_1996 = next((r for r in rams if r.id == 1996), None)

print(f"\n=== RAM 783 (Patriot Viper Steel 8GB) ===")
if viper_783:
    print(f"  Name: {viper_783.name}")
    print(f"  Normalized name: {viper_783.normalized_name}")
    print(f"  Search keywords: {viper_783.search_keywords}")
    print(f"  Capacity: {viper_783.capacity_gb}")
    print(f"  Speed: {viper_783.speed}")
    
    # Check if viper steel is in searchable_names
    viper_norm = normalize_text(viper_783.name)
    print(f"  Checking if '{viper_norm}' in searchable_names: {viper_norm in ram_matcher.searchable_names}")

print(f"\n=== RAM 1996 (Crucial) ===")
if crucial_1996:
    print(f"  Name: {crucial_1996.name}")
    print(f"  Normalized name: {crucial_1996.normalized_name}")
    print(f"  Search keywords: {crucial_1996.search_keywords}")
    print(f"  Capacity: {crucial_1996.capacity_gb}")

# Extract capacity
ram_capacity = 8  # From "2 x 4GB"
ram_ddr = "DDR4"
ram_freq = "3200"

print(f"\n=== Scoring candidates ===")
print(f"Listing normalized: {normalized[:100]}...")

# Score Viper Steel
if viper_783:
    score, method = ram_matcher._score_ram_match(
        viper_783, normalized, ram_capacity, ram_ddr, None, None
    )
    print(f"\nViper Steel (ID 783) score: {score}, method: {method}")

# Score Crucial
if crucial_1996:
    score, method = ram_matcher._score_ram_match(
        crucial_1996, normalized, ram_capacity, ram_ddr, None, None
    )
    print(f"Crucial (ID 1996) score: {score}, method: {method}")

# Check candidates by brand
print(f"\n=== Checking brand candidates ===")
brand_tokens = ram_matcher._extract_ram_tokens(listing_text)
print(f"Brand tokens: {brand_tokens}")

brands_in_title = set()
for token in brand_tokens:
    if isinstance(token, tuple):
        continue
    if isinstance(token, str) and token.lower() in ['corsair', 'kingston', 'gskill', 'g.skill', 'crucial',
                             'teamgroup', 'adata', 'patriot', 'silicon power',
                             'klevv', 'netac', 'acer', 'hp', 'dell', 'lexar',
                             'apacer', 'mushkin', 'geil', 'thermaltake', 'neo forza',
                             'hynix', 'skhynix', 'sk hynix', 'hyperx']:
        brands_in_title.add(token.lower())

print(f"Brands in title: {brands_in_title}")

# Get candidates
candidates = []
for brand in brands_in_title:
    if brand in ram_matcher.brand_to_rams:
        candidates.extend(ram_matcher.brand_to_rams[brand])

print(f"Number of candidates: {len(candidates)}")

# Check if patriot is in candidates
patriot_candidates = [c for c in candidates if 'patriot' in c.name.lower()]
print(f"Patriot candidates: {len(patriot_candidates)}")
for c in patriot_candidates[:3]:
    print(f"  - ID {c.id}: {c.name}")

# Check brand_to_rams for patriot
print(f"\n=== brand_to_rams keys ===")
patriot_in_keys = any('patriot' in k for k in ram_matcher.brand_to_rams.keys())
print(f"Patriot in brand_to_rams keys: {patriot_in_keys}")
for key in sorted(ram_matcher.brand_to_rams.keys())[:20]:
    print(f"  {key}: {len(ram_matcher.brand_to_rams[key])} RAMs")
