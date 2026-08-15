# -*- coding: utf-8 -*-
"""Debug alnnx RAM - should be ID 3289 (Kingston HyperX 16GB)."""
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

# Check RAM 3289
ram_3289 = next((r for r in rams if r.id == 3289), None)
if ram_3289:
    print(f"RAM 3289 (Kingston HyperX 16GB):")
    print(f"  Name: {ram_3289.name}")
    print(f"  Normalized: {ram_3289.normalized_name}")
    print(f"  Keywords: {ram_3289.search_keywords}")
    print(f"  Capacity: {ram_3289.capacity_gb}")
    print(f"  Speed: {ram_3289.speed}\n")

# Extract RAM info
import re
ram_capacity = 16  # From text
ram_ddr = "DDR4"   # From text
ram_speed = "3200" # From text

# Match RAM
print("=== RAM Match Result ===")
result = matcher.match_listing(text, extracted_capacity=ram_capacity, 
                                extracted_ddr=ram_ddr, extracted_speed=ram_speed)
if result.ram:
    print(f"Matched: ID {result.ram.id} - {result.ram.name}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.method}")
else:
    print("No RAM matched!")

# Check what HyperX RAMs are in database
print("\n=== HyperX RAMs in Database ===")
for ram in rams:
    if ram.name and 'hyperx' in ram.name.lower():
        if ram.capacity_gb == 16:
            print(f"ID {ram.id}: {ram.name}")
            print(f"  Normalized: {ram.normalized_name}")
