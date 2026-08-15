# -*- coding: utf-8 -*-
"""Debug specific issues from CLI output."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    RAMReferenceRepository, SSDReferenceRepository, MonitorRepository
)
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    rams = RAMReferenceRepository.get_all(session)
    ssds = SSDReferenceRepository.get_all(session)
    monitors = MonitorRepository.get_all(session)

# Issue 1: pbdhn RAM - "Patriot Viper Steel" should match ID 783
print("=" * 70)
print("Issue 1: pbdhn RAM - Patriot Viper Steel 8GB (ID 783)")
print("=" * 70)

text = """DDR4 Patriot Viper Steel 2x4GB (8GB) 3200Mhz"""
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Check keywords for ID 783
ram_783 = next((r for r in rams if r.id == 783), None)
if ram_783:
    print(f"\nRAM 783 keywords: {ram_783.search_keywords}")
    print(f"Normalized name: {ram_783.normalized_name}")

# Check if any keywords match
for kw in ram_783.search_keywords if ram_783 else []:
    if kw in normalized:
        print(f"  Keyword '{kw}' matches!")

# Issue 2: eiklm GPU - "Bez videokartes" should mean NO GPU
print("\n" + "=" * 70)
print("Issue 2: eiklm GPU - Should be NO GPU (Bez videokartes)")
print("=" * 70)

# Check GPU matcher behavior
from src.scraper.matcher import GPUMatcher
gpu_matcher = GPUMatcher([])

text = """Procesors: Ryzen 7 5800X3D"""
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Issue 3: fpokc SSD - Should be ID 453 (Crucial MX500), not ID 587
print("\n" + "=" * 70)
print("Issue 3: fpokc SSD - Should be ID 453 (Crucial MX500)")
print("=" * 70)

text = """Cietie diski: SSD Crucial MX500 1TB"""
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Check what SSDs have "crucial" and "mx500"
print("\nMatching SSDs:")
for ssd in ssds:
    if 'crucial' in ssd.brand.lower():
        if 'mx500' in ssd.model.lower():
            print(f"  ID {ssd.id}: {ssd.brand} {ssd.model} {ssd.capacity_gb}GB")

# Check SSD 587
ssd_587 = next((s for s in ssds if s.id == 587), None)
if ssd_587:
    print(f"\nSSD 587: {ssd_587.brand} {ssd_587.model}")
    print(f"  Keywords: {ssd_587.search_keywords}")

# Check SSD 453
ssd_453 = next((s for s in ssds if s.id == 453), None)
if ssd_453:
    print(f"\nSSD 453: {ssd_453.brand} {ssd_453.model}")
    print(f"  Keywords: {ssd_453.search_keywords}")
