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

# acgdx description
desc = """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)
Полностью рабочий компьютер, подходит для игр и повседневных задач.
Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)
Видеокарта: Nvidia GeForce GTX 1650 (4GB)
Оперативная память: 16GB DDR4 3200 MHz
SSD: 1TB Kingston NV1
HDD: 2TB Seagate
Блок питания: 650W
procesors:intel core i5procesora frekvence, ghz:2.60pamat plate:gigabyte h510m hvideo:nvidia geforce gtx 1650operatīvā atmiņa, gb:16hdd apjoms, gb:2000dvd:-stāvoklis:lietota"""

print("Testing acgdx issues...")
full_text = desc
normalized = normalize_text(full_text)

print(f"\nNormalized text:\n{normalized[:200]}...")

# Check SSD
print("\n=== SSD CHECK ===")
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"SSD Capacity extracted: {ssd_capacity}")

ssd_match = cm.ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
if ssd_match.ssd:
    print(f"SSD Match: {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"  Method: {ssd_match.method}")
else:
    print("No SSD match")

# Check Motherboard  
print("\n=== MOTHERBOARD CHECK ===")
print(f"'h510m' in normalized: {'h510m' in normalized}")
print(f"'h510' in normalized: {'h510' in normalized}")
print(f"'gigabyte' in normalized: {'gigabyte' in normalized}")

mb_match = cm.motherboard_matcher.match(desc, "")
if mb_match.motherboard:
    print(f"Motherboard: {mb_match.motherboard.brand} {mb_match.motherboard.model} (ID: {mb_match.motherboard.id})")
    print(f"  Method: {mb_match.method}")
else:
    print("No motherboard match")

# Check RAM
print("\n=== RAM CHECK ===")
ram_capacity = cm._extract_ram_capacity(full_text)
ram_ddr = cm._extract_ram_ddr_type(full_text)
print(f"RAM Capacity: {ram_capacity}")
print(f"RAM DDR: {ram_ddr}")

# Run full match
result = cm.match("Test", desc, 300.0)
print("\n=== FULL MATCH RESULT ===")
print(f"SSD: {result.ssd}")
print(f"Motherboard: {result.motherboard}")
