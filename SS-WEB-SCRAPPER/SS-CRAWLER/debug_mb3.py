# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
import re

# Full text
text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Мат. пл. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""

normalized = normalize_text(text)
print("Full normalized text:")
print(normalized)
print()

# Check if gigabyte h310m s2h 2.0 is in the normalized text
search = "gigabyte h310m s2h 2.0"
print(f"\nLooking for '{search}':")
print(f"  Found in normalized: {search in normalized}")

# Check MB context extraction
lines = text.lower().split('\n')
print("\n" + "="*60)
print("Checking lines for motherboard context:")

mb_keywords = ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']
for i, line in enumerate(lines):
    if any(kw in line for kw in mb_keywords):
        print(f"Line {i}: '{line}'")

# Check what happens with normalize_text
print("\n" + "="*60)
print("After normalize_text, checking if search pattern exists:")

# Check the whole normalized text
print(f"Full normalized: {repr(normalized[:200])}...")
print(f"Search pattern: {repr(search)}")
print(f"Match: {search in normalized}")
