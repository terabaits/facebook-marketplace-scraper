import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

import re

# Test text from listing
text = """Pārdodu PC

Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng"""

text_lower = text.lower()

# Check inclusion patterns
inclusion_patterns = [
    r'monitors?\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
    r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+monitors?',
    r'(?i)monitors?\s+(?:\d{2,3})["\']?\s*(?:collas|inch|in|\")',
    r'(?i)(?:\d{2,3})["\']?\s*(?:collas|inch|in|\\")\s+monitors?',
    r'(?i)hp\s+(?:\d{2,3})\s+collas',
]

print(f"Text: {text_lower}\n")

for pattern in inclusion_patterns:
    match = re.search(pattern, text_lower)
    if match:
        print(f"Pattern matched: {pattern[:50]}...")
        print(f"  Match: '{match.group()}'")
    else:
        print(f"Pattern NOT matched: {pattern[:50]}...")
