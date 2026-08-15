# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
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
    mbs = MotherboardRepository.get_all(session)

matcher = MotherboardMatcher(mbs)

# Full acgdx description
desc = """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)
pamat plate:: Gigabyte H510M H
video:: Nvidia geforce gtx 1650"""

normalized = normalize_text(desc)
print("Testing acgdx motherboard matching...")
print(f"Normalized: {normalized}\n")

# Check mb_context extraction
lines = desc.lower().split('\n')
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
mb_context = ' '.join(mb_context_lines)
mb_context_norm = normalize_text(mb_context)

print(f"MB Context: {mb_context}")
print(f"MB Context Norm: {mb_context_norm}\n")

# Check if gigabyte is in mb_context
print(f"'gigabyte' in mb_context: {'gigabyte' in mb_context}")
print(f"'gigabyte' in mb_context_norm: {'gigabyte' in mb_context_norm}")
print(f"'h510m' in mb_context_norm: {'h510m' in mb_context_norm}")

# Check exact match
test_names = ['gigabyte h510m h', 'gigabyte h510m']
for name in test_names:
    print(f"\n'{name}' in mb_context_norm: {name in mb_context_norm}")

# Check sorted names
print("\n=== Sorted brand+model names ===")
from src.utils.text import normalize_text
sorted_names = sorted(matcher.brand_model_names.items(), key=lambda x: len(x[0]), reverse=True)
gigabyte_mbs = [(name, mb) for name, mb in sorted_names if 'gigabyte' in name and 'h510' in name]
for name, mb in gigabyte_mbs[:5]:
    in_context = name in mb_context_norm
    print(f"  '{name}' -> ID {mb.id} ({mb.model}) - in context: {in_context}")
