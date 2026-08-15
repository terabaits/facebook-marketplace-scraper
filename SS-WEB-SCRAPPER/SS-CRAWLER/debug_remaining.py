# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository,
    MotherboardRepository, MonitorRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    cm = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSURepository.get_all(session),
        cases=CaseRepository.get_all(session),
        motherboards=MotherboardRepository.get_all(session),
        monitors=MonitorRepository.get_all(session)
    )

# Test aacph - Motherboard and Monitor
desc_aacph = """Itel Core i5-9400f Coffee Lake 2.90 Ghz
Мат. пл. Gigabyte H310M S2H 2.0
G. Skill Ddr4-2666 32gb
Gigabyte Nvidia GeForce GTX 1660 6gb DDR5
SDD 512gb HDD 500gb
Windows 10
Monitor: AOC 25" LCD 2590G4
Riga, Jelgava, Dobele."""

# Test dpfex - Dual SSDs and Monitor
desc_dpfex = """Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb
Var dabūt nedaudz lētak ar RAM 1x 16Gb
Monitors HP 24 collas dāvana
Atrodās Salaspilī"""

print("=" * 70)
print("aacph - Motherboard and Monitor")
print("=" * 70)
full_text = desc_aacph
normalized = normalize_text(full_text)

# Check motherboard patterns
print(f"\nMotherboard check:")
print(f"  'h310m' in normalized: {'h310m' in normalized}")
print(f"  's2h' in normalized: {'s2h' in normalized}")
print(f"  'gigabyte' in normalized: {'gigabyte' in normalized}")

# Check monitor patterns
print(f"\nMonitor check:")
print(f"  'aoc' in normalized: {'aoc' in normalized}")
print(f"  '2590g4' in normalized: {'2590g4' in normalized}")
print(f"  '25' in normalized: {'25' in normalized}")
print(f"  'monitor' in normalized: {'monitor' in normalized}")

# Run full match
result = cm.match("Test", desc_aacph, 550.0)
print(f"\n  Motherboard: {result.motherboard}")
print(f"  Monitor: {result.monitor}")

print("\n" + "=" * 70)
print("dpfex - Dual SSDs and Monitor")
print("=" * 70)
full_text = desc_dpfex
normalized = normalize_text(full_text)

# Check dual SSDs
print(f"\nDual SSD check:")
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"  SSD Capacity extracted: {ssd_capacity}")
print(f"  '128gb' in normalized: {'128gb' in normalized}")
print(f"  '500gb' in normalized: {'500gb' in normalized}")

# Check monitor
print(f"\nMonitor check:")
print(f"  'hp' in normalized: {'hp' in normalized}")
print(f"  '24' in normalized: {'24' in normalized}")
print(f"  'collas' in normalized: {'collas' in normalized}")
print(f"  'monitors' in normalized: {'monitors' in normalized}")

result = cm.match("Test", desc_dpfex, 230.0)
print(f"\n  SSD: {result.ssd}")
print(f"  Additional SSDs: {result.additional_ssds}")
print(f"  Monitor: {result.monitor}")
