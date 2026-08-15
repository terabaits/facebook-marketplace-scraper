#!/usr/bin/env python3
"""Debug RAM matching for fgfbp - check computer_matcher logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository, RAMReferenceRepository, PSURepository
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# The actual text from the listing
listing_text = """Pārdod datoru. Asus prime b760m-a wifi
intel i5 14400f
ram g. Skill f4 3000 c16d -32gb
ssd xlr8 cs3140 nvme m. 2 -1tb 7500mb/s
hdd seagate st2000nm0011 -2tb
aio cougar poseidon vistek argb 240
psu xfx xtr750 80+gold
gpu radeon rx 9060 xt 16gb
case ft418 white
Procesors:
I5 14400F
Procesora frekvence, Ghz:
4.50
Pamat plate:
Asus prime b760m-a wifi
Video:
Radeon rx 9060 xt
Operatīvā atmiņa, Gb:
32
HDD apjoms, Gb:
2000"""

full_text = listing_text
text_lower = full_text.lower()
normalized = normalize_text(full_text)

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    ram_matcher = RAMMatcher(rams)
    
    # Extract RAM info
    def _extract_ram_capacity(text):
        patterns = [r'(\d+)\s*GB\s*RAM', r'(\d+)\s*GB\s*DDR', r'RAM\s*(\d+)\s*GB', r'(\d+)\s*gb\s*ram']
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        # Also look for standalone GB near RAM keywords
        ram_keywords = ['ram', 'atmina', 'atmiņa', 'operativ', 'operatīv']
        for kw in ram_keywords:
            if kw in text.lower():
                kw_pos = text.lower().find(kw)
                segment = text[max(0, kw_pos-20):kw_pos+50]
                match = re.search(r'(\d+)\s*[Gg][Bb]', segment)
                if match:
                    return int(match.group(1))
        return None
    
    def _extract_ram_ddr_type(text):
        match = re.search(r'DDR(\d+)', text, re.IGNORECASE)
        if match:
            return f"DDR{match.group(1)}"
        return None
    
    def _extract_ram_frequency(text):
        match = re.search(r'(DDR\d*-\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
    
    ram_capacity = _extract_ram_capacity(full_text)
    ram_ddr_type = _extract_ram_ddr_type(full_text)
    ram_speed = _extract_ram_frequency(full_text)
    
    print("="*60)
    print("COMPUTER_MATCHER RAM LOGIC DEBUG")
    print("="*60)
    
    print(f"\nExtracted RAM capacity: {ram_capacity}")
    print(f"Extracted RAM DDR type: {ram_ddr_type}")
    print(f"Extracted RAM speed: {ram_speed}")
    
    # Match RAM
    ram_match = ram_matcher.match_listing(
        full_text,
        extracted_capacity=ram_capacity,
        extracted_ddr=ram_ddr_type,
        extracted_speed=ram_speed
    )
    
    print(f"\nMatched RAM: {ram_match.ram.name if ram_match.ram else 'None'}")
    print(f"Method: {ram_match.method}")
    
    # Check is_specific_ram logic
    is_specific_ram = False
    if ram_match.ram:
        ram_name_lower = ram_match.ram.name.lower()
        brand = ram_name_lower.split()[0] if ram_name_lower else ""
        
        print(f"\nRAM name lower: {ram_name_lower}")
        print(f"Brand extracted from RAM name: '{brand}'")
        
        # Check if brand is in text (allow for word boundaries)
        # Normalize brand name to handle "G.Skill" vs "gskill" variations
        brand_norm = brand.replace('.', '')  # Remove dots (e.g., "g.skill" -> "gskill")
        has_brand = brand in normalized or brand_norm in normalized
        
        print(f"Brand normalized: '{brand_norm}'")
        print(f"'brand' in normalized: {brand in normalized}")
        print(f"'brand_norm' in normalized: {brand_norm in normalized}")
        print(f"has_brand: {has_brand}")
        
        # Check for model series keyword in text
        model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                          'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                          't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                          'viper', 'steel', 'patriot', 'hyperx', 'aegis']
        has_model_in_text = False
        for kw in model_keywords:
            if kw in ram_name_lower and kw in normalized:
                has_model_in_text = True
                print(f"  Found model keyword: '{kw}'")
                break
        
        print(f"has_model_in_text: {has_model_in_text}")
        
        # Check for G.Skill model pattern match (e.g., F4-3200C16D)
        has_gskill_model = 'gskill' in normalized and re.search(r'f\d+[\s-]?\d+c\d+d', normalized)
        
        print(f"'gskill' in normalized: {'gskill' in normalized}")
        gskill_pattern = re.search(r'f\d+[\s-]?\d+c\d+d', normalized)
        print(f"G.Skill pattern match: {gskill_pattern}")
        print(f"has_gskill_model: {has_gskill_model}")
        
        is_exact = ram_match.method.split('+')[0] == 'exact'
        is_model_part = 'model_part' in ram_match.method
        is_gskill_match = 'gskill_freq' in ram_match.method or 'gskill_cap' in ram_match.method
        
        print(f"\nis_exact: {is_exact}")
        print(f"is_model_part: {is_model_part}")
        print(f"is_gskill_match: {is_gskill_match}")
        
        # Accept if: exact match, OR model_part with brand AND model in text, OR G.Skill pattern match
        if is_exact:
            is_specific_ram = True
            print("\nMatch accepted because is_exact=True")
        elif is_model_part and has_brand and has_model_in_text:
            is_specific_ram = True
            print("\nMatch accepted because is_model_part AND has_brand AND has_model_in_text")
        elif is_gskill_match and has_gskill_model:
            is_specific_ram = True
            print("\nMatch accepted because is_gskill_match AND has_gskill_model")
        else:
            is_specific_ram = False
            print("\nMatch REJECTED - no criteria met")
    
    print(f"\nFinal is_specific_ram: {is_specific_ram}")
    print(f"RAM would be accepted: {ram_match.ram and is_specific_ram}")
