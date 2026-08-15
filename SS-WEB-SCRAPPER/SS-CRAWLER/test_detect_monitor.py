# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
import re

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

print("Full text:")
print(full_text)
print()

# Simulate _detect_monitor_mentioned
text_lower = full_text.lower()

inclusion_patterns = [
    r'monitors?\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
    r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+monitors?',
    r'(?:ekrans|displejs|displays?)\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
    r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+(?:ekrans|displejs|displays?)',
    r'(?i)monitors?\s+(?:\d{2,3})["\']?\s*(?:collas|inch|in|\")',
    r'(?i)(?:\d{2,3})["\']?\s*(?:collas|inch|in|\\")\s+monitors?',
    r'monitors?\s+(?:dāvan|gift|included|komplekt|līdzi)',
    r'(?:dāvan|gift|included|komplekt|līdzi)\s+monitors?',
    r'ekrans\s+(?:dāvan|gift|included|komplekt|līdzi)',
    r'displejs\s+(?:dāvan|gift|included|komplekt|līdzi)',
    r'(?i)monitors?\s+(?:\d{2,3})\s+(?:collas|inch)',
    r'(?i)hp\s+(?:\d{2,3})\s+collas',
    r'(?i)lg\s+(?:\d{2,3})\s+collas',
    r'(?i)dell\s+(?:\d{2,3})\s+collas',
    r'(?i)asus\s+(?:\d{2,3})\s+collas',
]

print("Checking patterns:")
for pattern in inclusion_patterns:
    match = re.search(pattern, text_lower)
    if match:
        print("  MATCHED: " + pattern[:50])
        print("    Group: '" + match.group() + "'")
    else:
        print("  NOT MATCHED: " + pattern[:50])

# Simple keyword check
monitor_keywords = ['monitors', 'ekrans', 'displejs', 'displays', 'screen']
print("\nSimple keyword check:")
for kw in monitor_keywords:
    if kw in text_lower:
        print("  Found: " + kw)
    else:
        print("  NOT found: " + kw)
