# -*- coding: utf-8 -*-
"""Debug RAM matching for alnnx listing."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER\\src')

import re
from rapidfuzz import fuzz

# Simulate the key matching logic
def normalize_text(text):
    """Normalize text for search matching."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# The text from the listing
text = """Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz"""
normalized = normalize_text(text)

print("=== RAM Matching Debug ===")
print(f"Text: {text}")
print(f"Normalized: {normalized}")
print()

# Extracted values
extracted_capacity = 16
extracted_ddr = "DDR4"
extracted_speed = "3200"

print(f"Extracted: {extracted_capacity}GB {extracted_ddr} {extracted_speed}MHz")
print()

# The two RAMs we're comparing
ram_110 = {
    'id': 110,  # Approximate line number
    'name': 'Kingston HyperX Fury 16 GB',
    'speed': 'DDR4-3200',
    'capacity_gb': 16
}

ram_3289 = {
    'id': 3289,
    'name': 'Kingston HyperX 16 GB',
    'speed': 'DDR4-4800',
    'capacity_gb': 16
}

def score_ram_match(ram, normalized_title, extracted_capacity, extracted_speed):
    """Simplified scoring logic."""
    score = 0.0
    method = ""
    
    ram_name = normalize_text(ram['name'])
    
    # Check for exact name match
    if ram_name in normalized_title:
        score = 100.0
        method = "exact"
    else:
        # Fuzzy match
        score = fuzz.token_set_ratio(normalized_title, ram_name)
        method = "fuzzy"
    
    # Check for alphanumeric-only name match
    ram_name_nospace = re.sub(r'[^a-z0-9]', '', ram_name)
    title_nospace = re.sub(r'[^a-z0-9]', '', normalized_title)
    if ram_name_nospace in title_nospace:
        score = max(score, 100.0)
        method = "exact_nospace"
    
    # Model parts match
    model_parts = ram['name'].lower().split()
    for part in model_parts:
        if len(part) >= 3:
            if part in normalized_title:
                score += 15
                method += "+model_part"
                break
            elif part == 'hyperx' and 'hiperx' in normalized_title:
                score += 12
                method += "+model_hiperx_typo"
                break
    
    # Speed matching
    if extracted_speed and ram['speed']:
        ram_freq_match = re.search(r'(\d{4})', ram['speed'])
        title_freq = int(extracted_speed) if extracted_speed else None
        
        if ram_freq_match and title_freq:
            ram_freq = int(ram_freq_match.group(1))
            if ram_freq == title_freq:
                score += 40
                method += "+freq_exact"
            else:
                freq_diff = abs(ram_freq - title_freq)
                if freq_diff <= 200:
                    score -= 15
                    method += "+freq_close"
                else:
                    freq_diff_pct = freq_diff / max(ram_freq, title_freq)
                    score -= 40 * (1 + freq_diff_pct)
                    method += "+freq_mismatch"
    
    # Capacity matching
    if extracted_capacity and ram['capacity_gb']:
        if extracted_capacity == ram['capacity_gb']:
            score += 40
            method += "+capacity_exact"
        else:
            capacity_diff = abs(extracted_capacity - ram['capacity_gb'])
            capacity_diff_pct = capacity_diff / max(extracted_capacity, ram['capacity_gb'])
            score -= 100 * capacity_diff_pct
            method += "+capacity_mismatch"
    
    return score, method

print("=== Scoring RAM 110 (Kingston HyperX Fury 16 GB DDR4-3200) ===")
score_110, method_110 = score_ram_match(ram_110, normalized, extracted_capacity, extracted_speed)
print(f"Score: {score_110:.2f}")
print(f"Method: {method_110}")
print()

print("=== Scoring RAM 3289 (Kingston HyperX 16 GB DDR4-4800) ===")
score_3289, method_3289 = score_ram_match(ram_3289, normalized, extracted_capacity, extracted_speed)
print(f"Score: {score_3289:.2f}")
print(f"Method: {method_3289}")
print()

print("=== Analysis ===")
if score_110 > score_3289:
    print(f"✓ CORRECT: RAM 110 would be selected (score {score_110:.2f} vs {score_3289:.2f})")
else:
    print(f"✗ ISSUE: RAM 3289 would be selected (score {score_3289:.2f} vs {score_110:.2f})")
    print("  The issue is likely the frequency mismatch penalty for DDR4-4800 vs 3200MHz")
