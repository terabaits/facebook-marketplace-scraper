# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# Test normalization
text = """Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana"""

normalized = normalize_text(text)
print("Normalized:")
print(normalized)
print()
print("'hp' in normalized:", 'hp' in normalized)
print("'24' in normalized:", '24' in normalized)
print()

# Check HP models that would match
if 'hp 24' in normalized:
    print("Found 'hp 24' in normalized")
