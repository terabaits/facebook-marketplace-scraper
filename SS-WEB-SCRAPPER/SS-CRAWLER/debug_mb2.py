# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.scraper.motherboard_matcher import MotherboardMatcher
from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)
db = get_db_manager()

# Test text from actual listing
text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Мат. пл. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""

# Check normalized text
normalized = normalize_text(text)
print("Normalized text:")
print(normalized)
print("\n" + "="*60)

with db.get_session() as session:
    motherboards = MotherboardRepository.get_all(session)
    
    # Get specific motherboards we're interested in
    mb_8231 = [mb for mb in motherboards if mb.id == 8231][0]  # Gigabyte H310M S2H 2.0
    mb_9083 = [mb for mb in motherboards if mb.id == 9083][0]  # MSI H310M PRO-D
    
    print("\nMotherboard 8231 (Gigabyte H310M S2H 2.0):")
    print(f"  Brand: {mb_8231.brand}")
    print(f"  Model: {mb_8231.model}")
    print(f"  Keywords: {mb_8231.search_keywords}")
    print(f"  Normalized: {normalize_text(f'{mb_8231.brand} {mb_8231.model}')}")
    
    print("\nMotherboard 9083 (MSI H310M PRO-D):")
    print(f"  Brand: {mb_9083.brand}")
    print(f"  Model: {mb_9083.model}")
    print(f"  Keywords: {mb_9083.search_keywords}")
    print(f"  Normalized: {normalize_text(f'{mb_9083.brand} {mb_9083.model}')}")
    
    # Test if exact matches would work
    mb_context = "mat pl gigabyte h310m s2h 20"  # Simplified from normalized
    print(f"\nMB context: {mb_context}")
    print(f"\n8231 normalized in context: {normalize_text('Gigabyte H310M S2H 2.0') in mb_context}")
    print(f"9083 normalized in context: {normalize_text('MSI H310M PRO-D') in mb_context}")
    
    # Check what the actual text contains
    print(f"\n'gigabyte' in normalized text: {'gigabyte' in normalized}")
    print(f"'h310m' in normalized text: {'h310m' in normalized}")
    print(f"'s2h' in normalized text: {'s2h' in normalized}")
    print(f"'msi' in normalized text: {'msi' in normalized}")
    print(f"'pro-d' in normalized text: {'pro-d' in normalized}")
    print(f"'pro d' in normalized text: {'pro d' in normalized}")
    print(f"'20' in normalized text: {'20' in normalized}")
    print(f"'2.0' in text: {'2.0' in text.lower()}")
