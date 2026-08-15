# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorReferenceRepository
from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    monitors = MonitorReferenceRepository.get_all(session)

matcher = ComputerMonitorMatcher(monitors)

# Test AOC monitor
text = """Monitor: AOC 25" LCD 2590G4"""

print("Testing AOC monitor matching...")
print(f"Text: '{text}'")

normalized = normalize_text(text)
print(f"Normalized: '{normalized}'")

# Check if AOC monitors exist
print("\n=== AOC Monitors in Database ===")
aoc_monitors = [m for m in monitors if m.brand and 'aoc' in m.brand.lower()]
for m in aoc_monitors[:10]:
    print(f"  ID {m.id}: {m.brand} {m.model} ({m.size or 'N/A'}")")

# Check if 2590G4 exists
print("\n=== Monitors with 2590 ===")
for m in monitors:
    if m.model and '2590' in m.model:
        print(f"  ID {m.id}: {m.brand} {m.model} ({m.size}")")

# Test matching
result = matcher.match(text, "")
print(f"\nMatch result: {result.monitor}")
if result.monitor:
    print(f"  Brand: {result.monitor.brand}")
    print(f"  Model: {result.monitor.model}")
    print(f"  Size: {result.monitor.size}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method}")
