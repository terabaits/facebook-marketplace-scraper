# -*- coding: utf-8 -*-
"""Debug motherboard matching for alnnx listing."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER\\src')

import re
from rapidfuzz import fuzz

def normalize_text(text):
    """Normalize text for search matching."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# The listing text
title = "Pc-Dators. Ryzen 5 1600x. Ddr4 16gb Hyperx."
description = """Procesors: Ryzen 5 1600x
Procesora frekvence, Ghz: 4
Pamat plate: B450
Video: Gtx 1060
Operatīvā atmiņa, Gb: 16"""

full_text = f"{title} {description}".strip()
normalized = normalize_text(full_text)

print("=== Motherboard Matching Debug ===")
print(f"Full text: {full_text}")
print(f"Normalized: {normalized}")
print()

# Extract motherboard context
lines = full_text.lower().split('\n')
mb_context_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        mb_context_lines.append(line)
        skip_next = False
        continue
    if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']):
        mb_context_lines.append(line)
        if i + 1 < len(lines):
            mb_context_lines.append(lines[i + 1])
            skip_next = True
mb_context = ' '.join(mb_context_lines) if mb_context_lines else normalized
mb_context = normalize_text(mb_context)

print(f"MB Context: {mb_context}")
print()

# Check keywords in mb_context
keywords = ['asus', 'tuf', 'b450', 'plus', 'gaming', 'b450-plus']
print("=== Keywords in MB Context ===")
for kw in keywords:
    print(f"  '{kw}' in mb_context: {kw in mb_context}")
print()

# The motherboards we're comparing
mb_tuf_plus = {
    'id': 7446,
    'brand': 'Asus',
    'model': 'TUF B450-PLUS GAMING',
    'chipset': 'B450',
    'socket': 'AM4'
}

mb_tuf_pro = {
    'id': 7447,
    'brand': 'Asus',
    'model': 'TUF B450-PRO GAMING',
    'chipset': 'B450',
    'socket': 'AM4'
}

def score_motherboard_match(mb, mb_context_text, full_normalized):
    """Simplified motherboard scoring."""
    score = 0.0
    method = ""
    
    mb_name = normalize_text(f"{mb['brand']} {mb['model']}")
    
    # Check for exact name match
    if mb_name in mb_context_text:
        score = 100.0
        method = "exact"
    else:
        # Fuzzy match
        score = fuzz.token_set_ratio(mb_context_text, mb_name)
        method = "fuzzy"
    
    # Chipset match bonus
    if mb['chipset'] and mb['chipset'].lower() in mb_context_text:
        score += 30
        method += "+chipset"
    
    # Socket match bonus
    if mb['socket'] and mb['socket'].lower() in full_normalized:
        score += 10
        method += "+socket"
    
    # Model parts match
    model_parts = mb['model'].lower().split()
    for part in model_parts:
        if len(part) >= 3 and part in mb_context_text:
            if part.lower() in ['gaming', 'pro', 'prime', 'plus', 'ultra']:
                if mb['chipset'] and mb['chipset'].lower() in mb_context_text:
                    score += 5
                    method += "+model_part"
                    break
            else:
                score += 5
                method += "+model_part"
                break
    
    return score, method

print("=== Scoring Motherboards ===")

print(f"\n--- MB 7446 (Asus TUF B450-PLUS GAMING) ---")
score_plus, method_plus = score_motherboard_match(mb_tuf_plus, mb_context, normalized)
print(f"Score: {score_plus:.2f}")
print(f"Method: {method_plus}")

print(f"\n--- MB 7447 (Asus TUF B450-PRO GAMING) ---")
score_pro, method_pro = score_motherboard_match(mb_tuf_pro, mb_context, normalized)
print(f"Score: {score_pro:.2f}")
print(f"Method: {method_pro}")

print("\n=== Analysis ===")
if score_plus > score_pro:
    print(f"✓ CORRECT: TUF B450-PLUS would be selected ({score_plus:.2f} vs {score_pro:.2f})")
elif score_pro > score_plus:
    print(f"✗ ISSUE: TUF B450-PRO would be selected ({score_pro:.2f} vs {score_plus:.2f})")
else:
    print(f"? Tie - both score {score_plus:.2f}")

# Check what exact matches would work
print("\n=== Checking Exact Match Variants ===")
variants_plus = [
    'asus tuf b450 plus gaming',
    'tuf b450 plus gaming',
    'b450 plus gaming',
    'tuf b450-plus gaming',
]

for variant in variants_plus:
    norm = normalize_text(variant)
    print(f"  '{norm}' in mb_context: {norm in mb_context}")
