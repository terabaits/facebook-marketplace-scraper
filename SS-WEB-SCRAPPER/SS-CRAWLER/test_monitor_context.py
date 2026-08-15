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

print("Testing _extract_monitor_context...")
monitor_context = matcher._extract_monitor_context(full_text)
print("Monitor context:")
print(repr(monitor_context))
print()

if monitor_context:
    print("Monitor context found, checking HP monitors...")
    for mon in monitors:
        if mon.brand and mon.brand.lower() == 'hp' and mon.size == '24':
            model_clean = normalize_text(mon.model)
            if model_clean in monitor_context:
                print(f"  MATCH: {mon.brand} {mon.model}")
