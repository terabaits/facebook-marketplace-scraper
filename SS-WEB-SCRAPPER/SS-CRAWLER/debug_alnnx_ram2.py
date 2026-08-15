# -*- coding: utf-8 -*-
"""Debug alnnx RAM - why is it showing generic?"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
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

# alnnx text
text = """Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz"""

print("=== alnnx RAM Debug ===")
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}\n")

# Match RAM
result = matcher.match_listing(text, extracted_capacity=16, extracted_ddr="DDR4", extracted_speed="3200")

if result.ram:
    print(f"Matched: ID {result.ram.id} - {result.ram.name}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.method}")
    print(f"\nRAM Brand: {result.ram.name.split()[0] if result.ram.name else 'None'}")
else:
    print("No RAM matched")

# Check computer_matcher logic simulation
print("\n=== Checking computer_matcher logic ===")
ram_match = result
if result.ram:
    ram_name_lower = result.ram.name.lower()
    brand = ram_name_lower.split()[0] if ram_name_lower else ""
    print(f"RAM brand: {brand}")
    
    # Check if brand in normalized
    has_brand = brand in normalized
    print(f"Brand '{brand}' in normalized: {has_brand}")
    
    # Check model keywords
    model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                      'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                      't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                      'viper', 'steel', 'patriot', 'hyperx', 'kingston']
    
    has_model_in_text = False
    for kw in model_keywords:
        if kw in ram_name_lower and kw in normalized:
            has_model_in_text = True
            print(f"  Model keyword '{kw}' found in both RAM name and text")
            
    print(f"\nhas_model_in_text: {has_model_in_text}")
