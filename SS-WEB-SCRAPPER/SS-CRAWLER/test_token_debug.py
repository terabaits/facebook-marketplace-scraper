# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text, extract_cpu_tokens

# Test text
text = """Procesors:

 Amd r5 1600"""

print("Original text:")
print(text)
print()

normalized = normalize_text(text)
print("Normalized:")
print(normalized)
print()

tokens = extract_cpu_tokens(text)
print(f"Tokens: {tokens}")

# Check what pattern would match "r5 1600"
import re

print("\nChecking patterns...")
# Check for AMD Ryzen patterns
original_patterns = [
    r'i[3579]\s*-\s*\d{3,5}\s*(?:kf|ks|k|f|t)?',
    r'ryzen\s*\d?\s*\d{3,4}\s*(?:x|xt|3d|x3d|g)?',
    r'ryzen\s*\d?\s*\d{4}x3d',
    r'r[3579]\s*\d{3,4}g',
    r'xeon\s*(?:[ew])?\d*[-]?\d{4}(?:\s*v\d+)?',
]

text_fixed = text.lower().replace('xenon', 'xeon').replace('phamtom', 'phenom')
for pattern in original_patterns:
    matches = re.findall(pattern, text_fixed, re.IGNORECASE)
    if matches:
        print(f"  Pattern '{pattern[:30]}...' matches: {matches}")
