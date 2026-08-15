# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text
import re

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    monitors = MonitorRepository.get_all(session)

# Test with actual listing text
title = "Pārdodu PC"
description = """Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng"""

full_text = f"{title} {description}".lower()
normalized = normalize_text(full_text)

print("Normalized text:")
print(normalized)
print()

# Simulate _extract_size_from_text
monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays']
lines = full_text.split('\n')
monitor_sections = []

for line in lines:
    line_lower = line.lower()
    if any(kw in line_lower for kw in monitor_keywords):
        monitor_sections.append(line_lower)

search_text = ' '.join(monitor_sections) if monitor_sections else full_text
print("Monitor sections:", monitor_sections)
print("Search text:", search_text)

size_patterns = [
    r'(\d{2,3}(?:\.\d)?)\s*["\']\s*(?:inch|in)?',
    r'(\d{2,3})\s*(?:inch|in|″)',
    r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',
    r'ekrans\w*\s+(?:\w+\s+)?(\d{2,3})\b',
    r'\+\s*(?:monitor|ekrans)?\s*[:\-]?\s*(\d{2,3})',
]

extracted_size = None
for pattern in size_patterns:
    match = re.search(pattern, search_text)
    if match:
        size = match.group(1)
        try:
            size_num = float(size)
            if 21 <= size_num <= 49:
                extracted_size = str(int(size_num))
                break
        except ValueError:
            pass

print("\nExtracted size:", extracted_size)

# Now find HP 24" monitors and check scoring
print("\nHP 24\" monitors:")
count = 0
for mon in monitors:
    if mon.brand and mon.brand.lower() == 'hp' and mon.size == '24':
        count += 1
        if count <= 3:  # Show first 3
            print(f"  ID {mon.id}: {mon.brand} {mon.model}")
            print(f"    Size: '{mon.size}' (type: {type(mon.size).__name__})")
            
            # Calculate score
            score = 0.0
            
            # Brand match
            brand_clean = normalize_text(mon.brand)
            if brand_clean in normalized:
                score += 0.30
                print(f"    Brand match (+0.30)")
            
            # Size match
            if mon.size and extracted_size:
                mon_size = str(int(float(mon.size))) if '.' in mon.size else mon.size
                print(f"    mon_size: '{mon_size}', extracted_size: '{extracted_size}'")
                if mon_size == extracted_size:
                    score += 0.15
                    print(f"    Size match (+0.15)")
            
            print(f"    Total score: {score}")

print(f"\nTotal HP 24\" monitors: {count}")
