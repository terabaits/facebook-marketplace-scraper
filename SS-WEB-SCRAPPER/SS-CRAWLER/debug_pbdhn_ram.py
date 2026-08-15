# -*- coding: utf-8 -*-
"""Debug pbdhn RAM matching."""
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

# pbdhn RAM text
text = """Operatīvā atmiņa: DDR4 Patriot Viper Steel 2x4GB (8GB) 3200Mhz CL16-18-18-36"""

print("=== pbdhn RAM Debug ===")
print(f"Text: {text}")
normalized = normalize_text(text)
print(f"Normalized: {normalized}\n")

# Check RAM 783
ram_783 = next((r for r in rams if r.id == 783), None)
if ram_783:
    print(f"RAM 783 (Patriot Viper Steel 8GB):")
    print(f"  Name: {ram_783.name}")
    print(f"  Normalized: {ram_783.normalized_name}")
    print(f"  Keywords: {ram_783.search_keywords}")
    print(f"  Capacity: {ram_783.capacity_gb}")
    print(f"  Speed: {ram_783.speed}")

# Check if keywords match
print("\n=== Keyword Matching ===")
for kw in ram_783.search_keywords if ram_783 else []:
    if kw in normalized:
        print(f"  Keyword '{kw}' MATCHES")
    else:
        print(f"  Keyword '{kw}' NOT found")

# Extract RAM info
print("\n=== Extracted Info ===")
# Capacity
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
        print(f"  Multi-stick: {sticks} x {per_stick}GB = {ram_capacity}GB")
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
result = matcher.match_listing(text, extracted_capacity=ram_capacity, 
                                extracted_ddr=ram_ddr, extracted_speed=ram_freq)
if result.ram:
    print(f"  Matched: ID {result.ram.id} - {result.ram.name}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
else:
    print("  No RAM matched!")
