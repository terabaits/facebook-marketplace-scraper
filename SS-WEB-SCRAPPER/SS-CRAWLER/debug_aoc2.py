# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
import re

# Test the text
text = """Monitor: AOC 25" LCD 2590G4"""

print("Testing AOC monitor text...")
print(f"Text: '{text}'")

normalized = normalize_text(text)
print(f"Normalized: '{normalized}'")

# Check extraction patterns
patterns = [
    r'(\d{2,3})\s*"',  # 24"
    r'(\d{2,3})\s*inch',  # 24 inch
    r'monitor\w*\s+(\d{2,3})',  # monitor 24
    r'\b(\d{2,3})\s*(?:inch|"|\')',  # 24" or 24'
]

print("\nSize extraction:")
for pattern in patterns:
    match = re.search(pattern, normalized)
    if match:
        print(f"  Pattern '{pattern}' matched: {match.group(1)}")

# Check model extraction
model_pattern = r'(?:aoc|hp|samsung|dell|lg|asus)\s+.*?\s+(\w{3,}\d{3,})'
match = re.search(model_pattern, normalized)
if match:
    print(f"\nModel extracted: {match.group(1)}")
else:
    print("\nNo model extracted")
