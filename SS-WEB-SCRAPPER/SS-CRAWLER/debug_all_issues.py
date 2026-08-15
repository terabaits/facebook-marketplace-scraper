# -*- coding: utf-8 -*-
"""Debug all three listing issues."""
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

# pbdhn - Check RAM and why SSD shows "None (ID: 585)"
print("=" * 70)
print("pbdhn - RAM Issue")
print("=" * 70)
desc = """Operatīvā atmiņa: DDR4 Patriot Viper Steel 2x4GB (8GB) 3200Mhz CL16-18-18-36
Cietie diski: SSD Crucial BX500 480GB + HDD WD Blue 1TB 7200RPM"""

normalized = normalize_text(desc)
print(f"Text: {desc}")
print(f"Normalized: {normalized}")

# Check RAM extraction
ram_capacity = cm._extract_ram_capacity(desc)
ram_ddr = cm._extract_ram_ddr_type(desc)
print(f"\nRAM Capacity: {ram_capacity}, DDR: {ram_ddr}")
print(f"'patriot' in normalized: {'patriot' in normalized}")
print(f"'viper' in normalized: {'viper' in normalized}")
print(f"'vipersteel' in normalized: {'vipersteel' in normalized}")

# Check SSD extraction
ssd_capacity = cm._extract_ssd_capacity(desc)
print(f"\nSSD Capacity extracted: {ssd_capacity}")

# Direct SSD match
ssd_match = cm.ssd_matcher.match_listing(desc, extracted_capacity=ssd_capacity)
print(f"SSD Match: {ssd_match.ssd}")
if ssd_match.ssd:
    print(f"  ID: {ssd_match.ssd.id}")
    print(f"  Name: {ssd_match.ssd.brand} {ssd_match.ssd.model}")

# Check GPU "bez videokartes"
print("\n" + "=" * 70)
print("eiklm - GPU 'bez videokartes' check")
print("=" * 70)
desc = """Video karte: Bez videokartes"""
print(f"Text: {desc}")
has_no_gpu = cm._has_no_gpu(desc)
print(f"_has_no_gpu(): {has_no_gpu}")

# Check what patterns match
no_gpu_patterns = [
    r'bez\s+videokartes',
    r'nav\s+videokartes',
    r'bez\s+gpu',
    r'no\s+gpu',
    r'integrētā\s+videokarte',
]
normalized = normalize_text(desc)
for pattern in no_gpu_patterns:
    match = __import__('re').search(pattern, normalized)
    print(f"  Pattern '{pattern}': {match is not None}")

# fpokc - Check why SSD isn't matching Crucial MX500
print("\n" + "=" * 70)
print("fpokc - SSD Issue")
print("=" * 70)
desc = """Cietie diski: SSD Crucial MX500 1TB"""
normalized = normalize_text(desc)
print(f"Text: {desc}")
print(f"Normalized: {normalized}")

ssd_capacity = cm._extract_ssd_capacity(desc)
print(f"SSD Capacity: {ssd_capacity}")

ssd_match = cm.ssd_matcher.match_listing(desc, extracted_capacity=ssd_capacity)
print(f"SSD Match: {ssd_match.ssd}")
if ssd_match.ssd:
    print(f"  ID: {ssd_match.ssd.id}")
    print(f"  Brand: {ssd_match.ssd.brand}")
    print(f"  Model: {ssd_match.ssd.model}")
