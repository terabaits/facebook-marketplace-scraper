# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import re

# Test with normalized text (quotes removed)
normalized = 'monitor aoc 25 lcd 2590g4'

print("Testing size extraction from normalized text...")
print(f"Text: '{normalized}'")

# Current pattern
pattern1 = r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b'
match = re.search(pattern1, normalized)
print(f"Pattern 'monitor + number': {match}")

# Better patterns for normalized text
patterns = [
    r'monitor\w*\s+(?:\w+\s+)?(\d{2,3})\b',  # monitor aoc 25 or monitor 25
    r'\b(\d{2,3})\s*(?:inch|collas?)',  # 25 inch or 25 collas (Latvian)
    r'\b(\d{2,3})\s*lcd\b',  # 25 lcd
]

print("\nSize patterns:")
for pattern in patterns:
    match = re.search(pattern, normalized)
    if match:
        print(f"  Pattern matched: {match.group(1)}")
    else:
        print(f"  No match for: {pattern[:40]}")
