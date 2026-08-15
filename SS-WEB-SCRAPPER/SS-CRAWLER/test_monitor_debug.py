"""Debug monitor matching for dpfex.html"""
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

print("=== FULL TEXT ===")
print(full_text)
print("\n=== NORMALIZED ===")
print(normalized)

print("\n=== EXTRACTED SIZE ===")
size = monitor_matcher._extract_size_from_text(full_text)
print(f"Size: {size}")

print("\n=== MONITOR CONTEXT ===")
monitor_context = monitor_matcher._extract_monitor_context(full_text)
print(f"Monitor context: '{monitor_context}'")

print("\n=== DETECT MONITOR MENTIONED ===")
is_included, detection_method = monitor_matcher._detect_monitor_mentioned(full_text)
print(f"Is included: {is_included}, Method: {detection_method}")

print("\n=== HAS EXPLICIT MONITOR CONTEXT ===")
has_explicit = monitor_matcher._has_explicit_monitor_context(full_text)
print(f"Has explicit: {has_explicit}")

print("\n=== BRAND CHECK ===")
# Check if hp is in monitor context
if 'hp' in monitor_context:
    print("✓ 'hp' found in monitor_context")
else:
    print("✗ 'hp' NOT found in monitor_context")
    
# Check if hp is in full text
if 'hp' in full_text:
    print("✓ 'hp' found in full_text")
    # Find position
    pos = full_text.find('hp')
    print(f"  Position: {pos}")
    print(f"  Surrounding: ...{full_text[max(0,pos-30):pos+50]}...")

print("\n=== ATTEMPTING FULL MATCH ===")
result = monitor_matcher.match_listing("Test Title", text)
print(f"Result: {result}")
