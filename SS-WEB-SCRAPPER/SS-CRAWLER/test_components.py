#!/usr/bin/env python3
"""Test component extraction for the listing."""
import sys
sys.path.insert(0, 'src')

from src.scraper.computer_matcher import ComputerMatcher

# Test text from HTML
test_text = """Jaudīgs un labs asus. Intel core i7-9700k / 16gb ram / 250gb ssd / 500gb hdd / geforce gtx 1070 ti

Procesors: Intel Core i7
Procesora frekvence, Ghz: 3.60
Pamat plate: 750Gb
Video: Geforce gtx 1070 ti
Operatīvā atmiņa, Gb: 750
HDD apjoms, Gb: 500"""

print("Testing component extraction...")
print("=" * 60)
print("Test text:")
print(test_text)
print()

# Test RAM extraction
print("=" * 60)
print("RAM EXTRACTION:")
print("=" * 60)
ram_capacity = ComputerMatcher._extract_ram_capacity(None, test_text)
print(f"Extracted RAM capacity: {ram_capacity} GB")

ram_ddr = ComputerMatcher._extract_ram_ddr_type(None, test_text)
print(f"Extracted RAM DDR: {ram_ddr}")

print()

# Test SSD extraction  
print("=" * 60)
print("SSD EXTRACTION:")
print("=" * 60)
ssd_capacity = ComputerMatcher._extract_ssd_capacity(None, test_text)
print(f"Extracted SSD capacity: {ssd_capacity} GB")

has_specific = ComputerMatcher._has_specific_ssd_mention(None, test_text)
print(f"Has specific SSD mention: {has_specific}")

print()

# Test normalized text
from src.utils.text import normalize_text
print("=" * 60)
print("NORMALIZED TEXT:")
print("=" * 60)
normalized = normalize_text(test_text)
print(normalized)

print()

# Check for "intel" in text
print("=" * 60)
print("'INTEL' CHECK:")
print("=" * 60)
print(f"'intel' in normalized: {'intel' in normalized}")
print(f"'intel core' in normalized: {'intel core' in normalized}")
