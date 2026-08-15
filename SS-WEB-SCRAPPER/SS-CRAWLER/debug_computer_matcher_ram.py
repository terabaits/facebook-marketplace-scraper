# -*- coding: utf-8 -*-
"""Debug pbdhn computer matcher RAM logic."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.scraper.ram_matcher import RAMMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
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
print(f"=== Testing RAM extraction ===")
print(f"Normalized text length: {len(normalized)}")

# Extract RAM capacity
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
        print(f"Multi-stick: {sticks} x {per_stick}GB = {ram_capacity}GB")
        break

# Extract DDR type
ddr_match = re.search(r'ddr(\d+)', normalized)
ram_ddr = f"DDR{ddr_match.group(1)}" if ddr_match else None
print(f"DDR type: {ram_ddr}")

# Extract frequency
freq_match = re.search(r'(\d{4})\s*mhz', normalized)
ram_freq = freq_match.group(1) if freq_match else None
print(f"Frequency: {ram_freq}")

# Now let's manually trace through the RAM matching logic
print("\n=== Checking RAM line extraction ===")
text_lower = normalized.lower()

# RAM keywords
ram_keywords = ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas', 'operatīva']
ram_line = ""
lines = text_lower.split('\n')
print(f"Total lines: {len(lines)}")

# Try to find line with RAM keywords
for line in lines:
    for kw in ram_keywords:
        if kw in line:
            ram_line = line
            print(f"Found RAM keyword '{kw}' in line: {line[:100]}")
            break
    if ram_line:
        break

if not ram_line:
    ram_line = text_lower
    print("No specific RAM line found, using full text")

print(f"\nRAM line contains 'viper': {'viper' in ram_line}")
print(f"RAM line contains 'steel': {'steel' in ram_line}")
print(f"RAM line contains 'crucial': {'crucial' in ram_line}")
print(f"RAM line: {ram_line[:200]}")

# Now let's check the RAM matching
print("\n=== Running RAM matcher ===")
ram_match = ram_matcher.match_listing(
    listing_text,
    extracted_capacity=ram_capacity,
    extracted_ddr=ram_ddr,
    extracted_speed=ram_freq
)

if ram_match.ram:
    print(f"RAM matcher returned: ID {ram_match.ram.id} - {ram_match.ram.name}")
    print(f"  Method: {ram_match.method}")
    print(f"  Confidence: {ram_match.confidence}")
    
    # Now check computer_matcher's validation
    ram_name_lower = ram_match.ram.name.lower()
    brand = ram_name_lower.split()[0] if ram_name_lower else ""
    print(f"\nBrand extracted: '{brand}'")
    
    # Check if brand is in RAM line
    brand_norm = brand.replace('.', '')
    has_brand = brand in ram_line or brand_norm in ram_line
    print(f"has_brand: {has_brand}")
    
    # Check model keywords
    model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                      'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                      't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                      'viper', 'steel', 'patriot', 'hyperx', 'aegis',
                      'vipersteel', 'viper steel']
    has_model_in_text = False
    for kw in model_keywords:
        if kw in ram_name_lower and kw in ram_line:
            print(f"Model keyword '{kw}' found in both RAM name and RAM line")
            has_model_in_text = True
            break
    print(f"has_model_in_text: {has_model_in_text}")
    
    # Simulate computer_matcher logic
    print("\n=== Simulating computer_matcher logic ===")
    is_exact = ram_match.method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in ram_match.method
    
    print(f"is_exact: {is_exact}")
    print(f"is_model_part: {is_model_part}")
    
    # This is the key issue - if has_brand is False, is_specific_ram will be False
    # even though we have viper AND steel in the text (compound model)
    
    # Let's check if compound model logic should work
    compound_models = {
        'viper': 'patriot',
        'trident': 'gskill',
        'ripjaws': 'gskill',
        'vengeance': 'corsair',
        'dominator': 'corsair',
        'ballistix': 'crucial',
        'fury': 'kingston',
    }
    
    print("\n=== Checking compound model logic ===")
    compound_model_matched = False
    for model_keyword, implied_brand in compound_models.items():
        if model_keyword in ram_name_lower and model_keyword in ram_line:
            # Check if compound model has multiple parts
            if 'steel' in ram_name_lower and 'steel' in ram_line and model_keyword == 'viper':
                print(f"Found compound model match: {model_keyword} + steel")
                compound_model_matched = True
                break
    
    print(f"compound_model_matched: {compound_model_matched}")
    
    # Now check if is_specific_ram would be True
    is_specific_ram = False
    if is_exact:
        is_specific_ram = True
        print("is_specific_ram = True (is_exact)")
    elif is_model_part and has_brand and has_model_in_text:
        is_specific_ram = True
        print("is_specific_ram = True (is_model_part + has_brand + has_model_in_text)")
    elif is_model_part and compound_model_matched:
        # This is what SHOULD happen for Viper Steel
        is_specific_ram = True
        print("is_specific_ram = True (compound model match override)")
    else:
        print(f"is_specific_ram = False")
        print(f"  Reason: is_model_part={is_model_part}, has_brand={has_brand}, has_model_in_text={has_model_in_text}, compound_model_matched={compound_model_matched}")
        
else:
    print("No RAM matched!")
