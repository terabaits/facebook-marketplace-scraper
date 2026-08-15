# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import re

text = """SSD: 1TB Kingston NV1"""
text_lower = text.lower()

print("Testing TB extraction patterns...")
print(f"Text: '{text}'")

patterns = [
    r'ssd\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*tb\b',
    r'(\d+(?:\.\d+)?)\s*tb\s+ssd\b',
    r'ssd\s+(\d+(?:\.\d+)?)\s*tb\b',
]

for pattern in patterns:
    match = re.search(pattern, text_lower, re.IGNORECASE)
    if match:
        print(f"  Pattern matched: {match.group()}")
        print(f"    Value: {match.group(1)}")
    else:
        print(f"  No match for: {pattern}")
