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

# Extract monitor context
monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays', 'screen']
lines = full_text.split('\n')
monitor_context_parts = []

for line in lines:
    line_lower = line.lower()
    if any(kw in line_lower for kw in monitor_keywords):
        monitor_context_parts.append(line_lower)

monitor_context = ' '.join(monitor_context_parts)
print("Monitor context:")
print(repr(monitor_context))
print()

# Extract size
size_patterns = [
    r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',
    r'ekrans\w*\s+(?:\w+\s+)?(\d{2,3})\b',
]

extracted_size = None
for pattern in size_patterns:
    match = re.search(pattern, monitor_context)
    if match:
        size = match.group(1)
        try:
            size_num = float(size)
            if 21 <= size_num <= 49:
                extracted_size = str(int(size_num))
                break
        except ValueError:
            pass

print("extracted_size:", extracted_size)
print()

# Check HP 27mq
print("Checking HP 27mq...")
for mon in monitors:
    if mon.brand and mon.brand.lower() == 'hp' and mon.model == 'HP 27mq':
        print(f"  {mon.brand} {mon.model}")
        print(f"    Size: {mon.size}")
        print(f"    Normalized model: '{normalize_text(mon.model)}'")
        
        # Simulate matching
        score = 0.0
        matches = []
        
        # Brand match
        brand_clean = normalize_text(mon.brand)
        if brand_clean in monitor_context:
            score += 0.30
            matches.append("brand")
            print("    Brand match!")
        
        # Model match
        model_clean = normalize_text(mon.model)
        print(f"    model_clean: '{model_clean}'")
        print(f"    in monitor_context: {model_clean in monitor_context}")
        
        escaped = re.escape(model_clean)
        pattern = r'(?i)\b' + escaped + r'\b'
        print(f"    regex pattern: {pattern}")
        model_full_match = re.search(pattern, monitor_context)
        print(f"    model_full_match: {model_full_match}")
        
        if model_full_match:
            score += 0.50
            matches.append("model_full")
            print("    Model full match!")
        else:
            # Check prefix
            if len(model_clean) >= 4:
                for i in range(len(model_clean), 3, -1):
                    model_prefix = model_clean[:i]
                    if model_prefix in monitor_context:
                        score += 0.35
                        matches.append("model_prefix")
                        print(f"    Model prefix match: '{model_prefix}'")
                        break
        
        # Size check
        if mon.size and extracted_size:
            mon_size = str(int(float(mon.size))) if '.' in mon.size else mon.size
            print(f"    mon_size: '{mon_size}', extracted_size: '{extracted_size}'")
            if mon_size == extracted_size:
                score += 0.15
                matches.append("size")
                print("    Size match!")
            else:
                print("    Size MISMATCH!")
                if not ("model_full" in matches or "model_prefix" in matches):
                    print("    Would reset score due to size mismatch!")
        
        print(f"    Final score: {score}")
        print(f"    Matches: {matches}")
