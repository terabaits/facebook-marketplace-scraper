# -*- coding: utf-8 -*-
"""Debug alnnx motherboard matching."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    mobos = MotherboardRepository.get_all(session)

matcher = MotherboardMatcher(mobos)

# alnnx text
text = """Pārdod spēļu datoru. Procesors: AMD Ryzen 5 1600X 3.6GHz, Mātesplate: Asus TUF B450-PLUS GAMING,
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz, Cietie diski: SSD 128GB + HDD 1TB,
Video karte: GTX 1060 3GB, Barošanas bloks: 500W, Korpuss: Fractal Design"""

print("=== alnnx Motherboard Debug ===")
normalized = normalize_text(text)
print(f"Normalized: {normalized}\n")

# Get motherboard context
lines = text.lower().split('\n')
mb_context_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        mb_context_lines.append(line)
        skip_next = False
        continue
    if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']):
        mb_context_lines.append(line)
        if i + 1 < len(lines):
            mb_context_lines.append(lines[i + 1])
            skip_next = True
mb_context = ' '.join(mb_context_lines) if mb_context_lines else normalized

print(f"MB Context: {mb_context}\n")

# Check exact matches
print("=== Checking Exact Matches ===")
for name, mb in sorted(matcher.brand_model_names.items(), key=lambda x: len(x[0]), reverse=True)[:20]:
    if name in mb_context:
        print(f"EXACT: '{name}' -> ID {mb.id}: {mb.brand} {mb.model}")

# Check both TUF Pro and TUF B450-PLUS GAMING
print("\n=== TUF Motherboards ===")
for name, mb in matcher.brand_model_names.items():
    if 'tuf' in name and 'b450' in name:
        print(f"ID {mb.id}: '{name}'")
        
print("\n=== TUF Pro Motherboards ===")
for name, mb in matcher.brand_model_names.items():
    if 'tuf' in name and 'pro' in name:
        print(f"ID {mb.id}: '{name}' -> {mb.model}")

# Now match
print("\n=== Match Result ===")
result = matcher.match_listing(text)
if result.motherboard:
    print(f"Matched: ID {result.motherboard.id} - {result.motherboard.brand} {result.motherboard.model}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.method}")
else:
    print("No match")
