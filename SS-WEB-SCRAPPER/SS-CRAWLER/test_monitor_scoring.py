"""Debug monitor scoring for dpfex.html"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
from src.scraper.computer_scraper import ComputerScraper
from src.utils.config import AppConfig
from src.utils.text import normalize_text
import re

config = AppConfig.from_yaml()

# Get monitors from database  
scraper = ComputerScraper(config)
scraper.initialize()
monitor_matcher = scraper.matcher.monitor_matcher

# Test text
text = """Datori un orgtehnika/Datori/ Pārdod
Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb
Var dabūt nedaudz lētak ar RAM 1x 16Gb
Monitors HP 24 collas dāvana"""

full_text = text.lower()
normalized = normalize_text(full_text)
monitor_context = monitor_matcher._extract_monitor_context(full_text)

print("=== CHECKING HP MONITORS ===")
print(f"Monitor context: '{monitor_context}'")

# Check all HP monitors
hp_monitors = [m for m in monitor_matcher.monitors if m.brand.lower() == 'hp']
print(f"\nFound {len(hp_monitors)} HP monitors")

# Check which HP monitors have size 24
hp_24_monitors = [m for m in hp_monitors if m.size and str(m.size) == '24']
print(f"HP 24\" monitors: {len(hp_24_monitors)}")
for m in hp_24_monitors[:5]:  # Show first 5
    print(f"  ID {m.id}: {m.brand} {m.model} (size: {m.size})")

print("\n=== BRAND MATCH CHECK ===")
# Simulate the brand check in the loop
for mon in hp_24_monitors[:3]:
    brand_clean = normalize_text(mon.brand)
    print(f"\nMonitor: {mon.brand} {mon.model}")
    print(f"  brand_clean: '{brand_clean}'")
    print(f"  in monitor_context: {brand_clean in monitor_context}")
    
    # Also check model
    model_clean = normalize_text(mon.model)
    print(f"  model_clean: '{model_clean}'")
    escaped = re.escape(model_clean)
    model_full_match = re.search(r'(?i)\b' + escaped + r'\b', monitor_context)
    print(f"  model_full_match: {model_full_match is not None}")
