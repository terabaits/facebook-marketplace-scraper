# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
import re

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    monitors = MonitorRepository.get_all(session)

# Initialize matcher
matcher = ComputerMonitorMatcher(monitors)

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
print("Testing _extract_size_from_text...")

# Check for monitor sections
monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays']
lines = full_text.split('\n')
monitor_sections = []

for line in lines:
    line_lower = line.lower()
    if any(kw in line_lower for kw in monitor_keywords):
        monitor_sections.append(line_lower)

search_text = ' '.join(monitor_sections) if monitor_sections else full_text
print("Monitor sections found:", len(monitor_sections))
if monitor_sections:
    print("Search text: '" + search_text + "'")

size_patterns = [
    r'(\d{2,3}(?:\.\d)?)\s*["\']\s*(?:inch|in)?',
    r'(\d{2,3})\s*(?:inch|in|″)',
    r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',
    r'ekrans\w*\s+(?:\w+\s+)?(\d{2,3})\b',
    r'\+\s*(?:monitor|ekrans)?\s*[:\-]?\s*(\d{2,3})',
]

for pattern in size_patterns:
    match = re.search(pattern, search_text)
    if match:
        print("Pattern matched: " + pattern)
        size = match.group(1)
        print("  Size: " + size)
        try:
            size_num = float(size)
            if 21 <= size_num <= 49:
                print("  -> VALID")
            else:
                print("  -> INVALID (not in range 21-49)")
        except ValueError:
            print("  -> ERROR parsing")
    else:
        print("NOT matched: " + pattern[:50])
