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
normalized = normalize_text(full_text)

print("Normalized:")
print(normalized)
print()

# Check model match for "HP 32"
model = "32"
model_clean = normalize_text(model)
print("Model clean: '" + model_clean + "'")

# Use word boundaries for model matching
escaped = re.escape(model_clean)
pattern = r'(?i)\b' + escaped + r'\b'
print("Pattern: '" + pattern + "'")

match = re.search(pattern, normalized)
if match:
    print("Model '32' matched at position: " + str(match.start()) + " - " + str(match.end()))
    print("Matched text: '" + match.group() + "'")
else:
    print("Model '32' NOT matched")

# Check for "32" in different contexts
print("\nChecking '32' contexts:")
import re
for m in re.finditer(r'\b32\b', normalized):
    start = max(0, m.start() - 20)
    end = min(len(normalized), m.end() + 20)
    print("  Position " + str(m.start()) + ": '" + normalized[start:end] + "'")
