# -*- coding: utf-8 -*-
"""Debug why HyperX fallback isn't working."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import RAMReferenceRepository
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)

# alnnx text
text = """Pārdod spēļu datoru.
Procesors: AMD Ryzen 5 1600X 3.6GHz
Mātesplate: Asus TUF B450-PLUS GAMING
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz
Cietie diski: SSD 128GB + HDD 1TB
Video karte: GTX 1060 3GB
Barošanas bloks: 500W
Korpuss: Fractal Design"""

normalized = normalize_text(text)
text_lower = normalized.lower()

print("=== Debugging HyperX Fallback ===")
print(f"Normalized: {normalized}\n")

# Check RAM context
ram_context_lines = []
for line in text_lower.split('\n'):
    if any(kw in line for kw in ['pamat plate', 'motherboard', 'mb:', 'plate', 'z370', 'z390', 'b360', 'b450', 'x570']):
        continue
    if any(kw in line for kw in ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas']):
        ram_context_lines.append(line)
ram_context = ' '.join(ram_context_lines)

print(f"RAM context: {ram_context}\n")

# Check if 'hyperx' in ram_context
print(f"'hyperx' in ram_context: {'hyperx' in ram_context}")

# Find HyperX RAMs
print("\n=== HyperX 16GB DDR4 RAMs ===")
for ram in rams:
    if 'hyperx' in ram.name.lower() and ram.capacity_gb == 16:
        ram_name_lower = ram.name.lower()
        brand_in_context = 'hyperx' in ram_context and 'hyperx' in ram_name_lower
        
        # Check DDR
        ram_ddr = None
        if ram.speed:
            ddr_match = re.search(r'ddr(\d+)', ram.speed.lower())
            if ddr_match:
                ram_ddr = f"DDR{ddr_match.group(1)}"
        
        print(f"ID {ram.id}: {ram.name}")
        print(f"  DDR: {ram_ddr}")
        print(f"  Brand in context: {brand_in_context}")
        print()
