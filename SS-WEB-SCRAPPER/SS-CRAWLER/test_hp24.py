# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re

# Test the new patterns
text = "monitors hp 24 collas dāvana"

# Test various patterns
patterns = [
    r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',  # "monitor 24" or "monitors hp 24"
    r'\bmonitors?\s+\w+\s+(\d{2,3})\b',  # "monitors hp 24" 
    r'hp\s+(\d{2,3})\s+collas',  # "hp 24 collas"
]

print("Text: '" + text + "'")
for pattern in patterns:
    match = re.search(pattern, text)
    if match:
        print("Pattern matched: " + pattern)
        print("  Group 0: '" + match.group(0) + "'")
        print("  Group 1: '" + match.group(1) + "'")
    else:
        print("Pattern NOT matched: " + pattern)
