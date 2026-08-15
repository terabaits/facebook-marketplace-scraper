# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# Test the version number issue
test_cases = [
    "Gigabyte H310M S2H 2.0",
    "gigabyte h310m s2h 2.0",
    "h310m s2h 2.0",
    "2.0",
    "G.Skill Aegis",
]

print("Testing normalization:")
for case in test_cases:
    norm = normalize_text(case)
    print(f"  '{case}' -> '{norm}'")

# Check the actual text
print("\n" + "="*60)
text = "Мат. пл. Gigabyte H310M S2H 2.0"
print(f"Original: '{text}'")
print(f"Normalized: '{normalize_text(text)}'")
