# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# Text from the listing
text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Мат. пл. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""

normalized = normalize_text(text)
print("Full normalized text:")
print(normalized)
print("\n" + "="*50)

# Check specific patterns
print("\nChecking specific patterns:")
print(f"Contains 'gskill': {'gskill' in normalized}")
print(f"Contains 'aegis': {'aegis' in normalized}")
print(f"Contains 'gigabyte h310m': {'gigabyte h310m' in normalized}")
print(f"Contains 'h310m s2h': {'h310m s2h' in normalized}")
print(f"Contains 's2h 2.0': {'s2h 2.0' in normalized}")
print(f"Contains 'aoc': {'aoc' in normalized}")
print(f"Contains '2590g4': {'2590g4' in normalized}")
print(f"Contains '2590': {'2590' in normalized}")
print(f"Contains 'g4': {'g4' in normalized}")

# Check the motherboard context
print("\n" + "="*50)
print("Checking motherboard context extraction:")
lines = text.lower().split('\n')
for i, line in enumerate(lines):
    if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard', 'мать']):
        print(f"Line {i}: {line}")
        # Check next line
        if i + 1 < len(lines):
            print(f"Next line: {lines[i + 1]}")

# Check RAM context
print("\n" + "="*50)
print("Checking RAM-related patterns:")
print(f"'g. skill' in text: {'g. skill' in text.lower()}")
print(f"'g.skill' in text: {'g.skill' in text.lower()}")
print(f"'ddr4-2666' in normalized: {'ddr4-2666' in normalized}")
print(f"'ddr4 2666' in normalized: {'ddr4 2666' in normalized}")

# Check monitor context
print("\n" + "="*50)
print("Checking monitor patterns:")
print(f"'monitor' in normalized: {'monitor' in normalized}")
print(f"'aoc 25' in normalized: {'aoc 25' in normalized}")
print(f"'2590g4' in normalized: {'2590g4' in normalized}")
print(f"'lcd' in normalized: {'lcd' in normalized}")

# What monitor model patterns exist
print("\n" + "="*50)
print("Checking for similar AOC monitors in DB:")
import sys
sys.path.insert(0, 'src')
from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    all_monitors = MonitorRepository.get_all(session)
    # Look for AOC monitors with 25" size
    aoc_25 = [m for m in all_monitors if 'aoc' in m.brand.lower() and m.size and float(m.size) == 25.0]
    print(f"AOC 25\" monitors found: {len(aoc_25)}")
    for m in aoc_25[:10]:
        print(f"  ID {m.id}: {m.brand} {m.model} - Size: {m.size}")
        print(f"    Keywords: {m.search_keywords}")
