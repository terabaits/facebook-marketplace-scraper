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
normalized = normalize_text(full_text)

print("Full test...")

# Call the full method
result = matcher.match_listing(title, description)
print("Result:", result)

# Check the extracted size
extracted_size = matcher._extract_size_from_text(full_text)
print("Extracted size:", extracted_size)

# Check if HP is in normalized
print("'hp' in normalized:", 'hp' in normalized)

# Check is_included
is_included, detection_method = matcher._detect_monitor_mentioned(full_text)
print("is_included:", is_included)
print("detection_method:", detection_method)

# Now simulate what match_listing does
print("\nSimulating match_listing logic...")

# Search through monitor references
best_match = None
best_score = 0.0
best_method = "none"

for mon in monitors:
    if mon.brand and mon.brand.lower() == 'hp' and mon.size == '24':
        print(f"\nChecking: {mon.brand} {mon.model}")
        
        score = 0.0
        matches = []
        
        # Check brand match
        brand_clean = normalize_text(mon.brand)
        if brand_clean in normalized:
            score += 0.30
            matches.append("brand")
            print("  Brand match!")
        
        # Check model match
        model_clean = normalize_text(mon.model)
        print(f"  Model clean: '{model_clean}'")
        print(f"  In normalized: {model_clean in normalized}")
        
        # Check size match
        if mon.size and extracted_size:
            mon_size = str(int(float(mon.size))) if '.' in mon.size else mon.size
            print(f"  mon_size: '{mon_size}', extracted_size: '{extracted_size}'")
            if mon_size == extracted_size:
                score += 0.15
                matches.append("size")
                print("  Size match!")
        
        print(f"  Score: {score}, Matches: {matches}")
        
        if score > best_score:
            best_score = score
            best_match = mon
            best_method = "+".join(matches) if matches else "fuzzy"

print(f"\nBest match: {best_match}")
print(f"Best score: {best_score}")
print(f"Best method: {best_method}")
