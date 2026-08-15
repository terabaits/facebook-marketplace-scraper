#!/usr/bin/env python3
"""Test fgfbp specific issues."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository, RAMReferenceRepository, PSURepository
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.utils.text import normalize_text, extract_cpu_tokens
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

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("="*60)
    print("TESTING FGFBP LISTING")
    print("="*60)
    
    # Normalize the text
    normalized = normalize_text(listing_text)
    print(f"\nNormalized text (first 500 chars):\n{normalized[:500]}\n")
    
    # === CPU TEST ===
    print("\n" + "="*60)
    print("CPU TEST: Should match i5-14400F (ID 14), not i5-14400 (ID 10)")
    print("="*60)
    
    cpus = CPUReferenceRepository.get_all(session)
    cpu_matcher = CPUMatcher(cpus)
    
    # Check tokens extracted
    tokens = extract_cpu_tokens(listing_text)
    print(f"\nExtracted CPU tokens: {tokens}")
    
    # Check for 14400 processors
    print("\nProcessors with '14400' in DB:")
    for cpu in cpus:
        if '14400' in cpu.cpu_name.lower():
            print(f"  ID {cpu.id}: {cpu.cpu_name} - processor_number='{cpu.processor_number}'")
    
    # Try matching
    cpu_result = cpu_matcher.match(listing_text)
    print(f"\nMatched CPU: {cpu_result.cpu.cpu_name if cpu_result.cpu else 'None'} (ID: {cpu_result.cpu.id if cpu_result.cpu else 'N/A'}, method: {cpu_result.method})")
    print(f"Confidence: {cpu_result.confidence}")
    
    # Check normalized text for i514400f
    print(f"\nLooking for 'i514400f' in normalized: {'i514400f' in normalized}")
    print(f"Looking for 'i514400' in normalized: {'i514400' in normalized}")
    
    # === RAM TEST ===
    print("\n" + "="*60)
    print("RAM TEST: Should match G.Skill F4-3200C16D-32GTZ (ID 3319)")
    print("Text has 'f4 3000 c16d' but DB has 'F4-3200C16D'")
    print("="*60)
    
    rams = RAMReferenceRepository.get_all(session)
    ram_matcher = RAMMatcher(rams)
    
    # Check what's in the text
    print(f"\nRAM-related text from listing:")
    for line in listing_text.split('\n'):
        if 'ram' in line.lower() or 'skill' in line.lower() or 'f4' in line.lower():
            print(f"  Line: '{line}'")
    
    print(f"\nNormalized RAM line: {normalize_text('ram g. Skill f4 3000 c16d -32gb')}")
    
    # Show ID 3319 details
    print("\nRAM ID 3319 in DB:")
    for ram in rams:
        if ram.id == 3319:
            print(f"  Name: {ram.name}")
            print(f"  Search keywords: {ram.search_keywords}")
    
    # Check for F4-3000 in DB
    print("\nRAMs with 'F4-3000' in DB:")
    for ram in rams:
        if 'f4-3000' in ram.name.lower() or 'f4 3000' in ram.name.lower():
            print(f"  ID {ram.id}: {ram.name}")
    
    # Try matching with extracted values
    ram_result = ram_matcher.match_listing(listing_text, extracted_capacity=32, extracted_ddr="DDR4")
    print(f"\nMatched RAM: {ram_result.ram.name if ram_result.ram else 'None'} (ID: {ram_result.ram.id if ram_result.ram else 'N/A'})")
    print(f"Method: {ram_result.method}, Confidence: {ram_result.confidence}")
    
    # === PSU TEST ===
    print("\n" + "="*60)
    print("PSU TEST: Should match XFX XTR 750W (ID 8593)")
    print("="*60)
    
    psus = PSURepository.get_all(session)
    psu_matcher = PSUMatcher(psus)
    
    # Check PSU line
    print(f"\nPSU-related text from listing:")
    for line in listing_text.split('\n'):
        if 'psu' in line.lower() or 'xfx' in line.lower() or 'xtr' in line.lower():
            print(f"  Line: '{line}'")
    
    # Check for XTR in DB
    print("\nXFX PSUs with 'XTR' in DB:")
    for psu in psus:
        if 'xtr' in psu.name.lower():
            print(f"  ID {psu.id}: {psu.name} - {psu.wattage}W")
    
    # Try matching
    psu_result = psu_matcher.match_listing(listing_text, price=None)
    print(f"\nMatched PSU: {psu_result.psu.name if psu_result.psu else 'None'} (ID: {psu_result.psu.id if psu_result.psu else 'N/A'})")
    print(f"Method: {psu_result.method}, Confidence: {psu_result.confidence}")
