#!/usr/bin/env python3
"""Debug computer matcher for fgfbp."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository, RAMReferenceRepository, PSURepository
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.scraper.computer_matcher import ComputerMatcher
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
    cpus = CPUReferenceRepository.get_all(session)
    rams = RAMReferenceRepository.get_all(session)
    psus = PSURepository.get_all(session)
    
    cpu_matcher = CPUMatcher(cpus)
    ram_matcher = RAMMatcher(rams)
    psu_matcher = PSUMatcher(psus)
    
    # Match CPU
    cpu_match = cpu_matcher.match(full_text)
    print("=" * 60)
    print("CPU MATCH")
    print("=" * 60)
    print(f"CPU: {cpu_match.cpu.cpu_name if cpu_match.cpu else 'None'} (ID: {cpu_match.cpu.id if cpu_match.cpu else 'N/A'})")
    print(f"Method: {cpu_match.method}")
    print(f"Confidence: {cpu_match.confidence}")
    
    # Match RAM
    print("\n" + "=" * 60)
    print("RAM MATCH")
    print("=" * 60)
    
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
    
    print(f"Extracted RAM capacity: {ram_capacity}")
    print(f"Extracted RAM DDR type: {ram_ddr_type}")
    print(f"Extracted RAM speed: {ram_speed}")
    
    ram_match = ram_matcher.match_listing(
        full_text,
        extracted_capacity=ram_capacity,
        extracted_ddr=ram_ddr_type,
        extracted_speed=ram_speed
    )
    
    print(f"\nMatched RAM: {ram_match.ram.name if ram_match.ram else 'None'} (ID: {ram_match.ram.id if ram_match.ram else 'N/A'})")
    print(f"Method: {ram_match.method}")
    print(f"Confidence: {ram_match.confidence}")
    
    if ram_match.ram:
        ram_name_lower = ram_match.ram.name.lower()
        brand = ram_name_lower.split()[0] if ram_name_lower else ""
        has_brand = brand in normalized
        
        print(f"\nRAM name: {ram_match.ram.name}")
        print(f"Brand extracted: '{brand}'")
        print(f"Has brand in normalized: {has_brand}")
        
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
        
        print(f"Has model in text: {has_model_in_text}")
        
        # Check for G.Skill model
        has_gskill_model = 'gskill' in normalized and re.search(r'f\d+[\s-]?\d+c\d+d', normalized)
        print(f"Has G.Skill model pattern: {has_gskill_model}")
        
        is_exact = ram_match.method.split('+')[0] == 'exact'
        is_model_part = 'model_part' in ram_match.method
        is_gskill_match = 'gskill_freq' in ram_match.method or 'gskill_cap' in ram_match.method
        
        print(f"\nis_exact: {is_exact}")
        print(f"is_model_part: {is_model_part}")
        print(f"is_gskill_match: {is_gskill_match}")
        
        is_specific_ram = False
        if is_exact:
            is_specific_ram = True
        elif is_model_part and has_brand and has_model_in_text:
            is_specific_ram = True
        elif is_gskill_match and has_gskill_model:
            is_specific_ram = True
        
        print(f"\nis_specific_ram: {is_specific_ram}")
    
    # Match PSU
    print("\n" + "=" * 60)
    print("PSU MATCH")
    print("=" * 60)
    
    psu_match = psu_matcher.match_listing(full_text, price=None)
    print(f"PSU: {psu_match.psu.name if psu_match.psu else 'None'} (ID: {psu_match.psu.id if psu_match.psu else 'N/A'})")
    print(f"Method: {psu_match.method}")
    print(f"Confidence: {psu_match.confidence}")
