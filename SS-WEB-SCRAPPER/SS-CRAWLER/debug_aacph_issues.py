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

# aacph description
desc = """Itel Core i5-9400f Coffee Lake 2.90 Ghz
Мат. пл. Gigabyte H310M S2H 2.0
G. Skill Ddr4-2666 32gb
Gigabyte Nvidia GeForce GTX 1660 6gb DDR5
SDD 512gb HDD 500gb
Windows 10
Monitor: AOC 25" LCD 2590G4
Riga, Jelgava, Dobele."""

print("Testing aacph issues...")
print(f"Description:\n{desc}\n")

full_text = desc
normalized = normalize_text(full_text)

# Check SSD extraction
print("=== SSD CHECK ===")
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"SSD Capacity extracted: {ssd_capacity}")

# The text has "SDD" (typo) not "SSD"
print(f"'ssd' in text: {'ssd' in full_text.lower()}")
print(f"'sdd' in text: {'sdd' in full_text.lower()}")

# Check RAM
print("\n=== RAM CHECK ===")
ram_capacity = cm._extract_ram_capacity(full_text)
ram_ddr = cm._extract_ram_ddr_type(full_text)
print(f"RAM Capacity: {ram_capacity}")
print(f"RAM DDR: {ram_ddr}")

# Check if G.Skill is detected
print(f"'g.skill' in normalized: {'g.skill' in normalized}")
print(f"'g skill' in normalized: {'g skill' in normalized}")

# Check motherboard
print("\n=== MOTHERBOARD CHECK ===")
print(f"'h310m' in normalized: {'h310m' in normalized}")
print(f"'h310' in normalized: {'h310' in normalized}")
print(f"'s2h' in normalized: {'s2h' in normalized}")

# Check monitor
print("\n=== MONITOR CHECK ===")
print(f"'aoc' in normalized: {'aoc' in normalized}")
print(f"'2590g4' in normalized: {'2590g4' in normalized}")
print(f"'25' in normalized: {'25' in normalized}")
