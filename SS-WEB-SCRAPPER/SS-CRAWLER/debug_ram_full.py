# -*- coding: utf-8 -*-
"""Debug RAM matching for alnnx listing - full computer_matcher simulation."""
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

def extract_ram_capacity(text):
    """Extract RAM capacity from text."""
    text_lower = text.lower()
    
    # Look for "16gb" or "16 gb" patterns
    match = re.search(r'(\d+)\s*gb', text_lower)
    if match:
        capacity = int(match.group(1))
        if 1 <= capacity <= 256:
            return capacity
    return None

def extract_ram_ddr_type(text):
    """Extract DDR type from text."""
    text_lower = text.lower()
    match = re.search(r'ddr(\d+)', text_lower)
    if match:
        return f"DDR{match.group(1)}"
    return None

def extract_ram_frequency(text):
    """Extract RAM frequency from text."""
    text_lower = text.lower()
    match = re.search(r'(\d{3,4})\s*mhz', text_lower)
    if match:
        return match.group(1)
    # Also check for patterns like "DDR4-3200"
    match = re.search(r'ddr\d+[-\s]*(\d{4})', text_lower)
    if match:
        return match.group(1)
    return None

# The listing text
title = "Pc-Dators. Ryzen 5 1600x. Ddr4 16gb Hyperx."
description = """Procesors: Ryzen 5 1600x
Procesora frekvence, Ghz: 4
Pamat plate: B450
Video: Gtx 1060
Operatīvā atmiņa, Gb: 16"""

full_text = f"{title} {description}".strip()
normalized = normalize_text(full_text)

print("=== Full Text Analysis ===")
print(f"Title: {title}")
print(f"Description: {description}")
print(f"Normalized: {normalized}")
print()

# Extract RAM info
ram_capacity = extract_ram_capacity(full_text)
ram_ddr_type = extract_ram_ddr_type(full_text)
ram_speed = extract_ram_frequency(full_text)

print(f"Extracted RAM: {ram_capacity}GB {ram_ddr_type} {ram_speed}MHz")
print()

# Check what's in the normalized text
print("=== Keywords in Normalized Text ===")
keywords_to_check = ['hyperx', 'fury', 'kingston', 'corsair', 'vengeance', 'ddr4', '3200', '4800']
for kw in keywords_to_check:
    print(f"  '{kw}' in normalized: {kw in normalized}")
print()

# Simulate the computer_matcher is_specific_ram check
# This is what the actual code checks

print("=== Simulating computer_matcher logic ===")

# The RAMs we're comparing
ram_111 = {
    'id': 111,
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

def check_is_specific_ram(ram, normalized_text, ram_match_method):
    """Simulate the is_specific_ram check from computer_matcher."""
    ram_name_lower = ram['name'].lower()
    brand = ram_name_lower.split()[0] if ram_name_lower else ""
    
    # Check if brand is in text
    brand_norm = brand.replace('.', '')
    has_brand = brand in normalized_text or brand_norm in normalized_text
    
    # Check for model series keyword in text
    model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                      'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                      't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                      'viper', 'steel', 'patriot', 'hyperx', 'aegis']
    has_model_in_text = False
    for kw in model_keywords:
        if kw in ram_name_lower and kw in normalized_text:
            has_model_in_text = True
            break
    
    is_exact = ram_match_method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in ram_match_method
    
    print(f"  Brand: '{brand}'")
    print(f"  has_brand: {has_brand}")
    print(f"  has_model_in_text: {has_model_in_text}")
    print(f"  is_exact: {is_exact}")
    print(f"  is_model_part: {is_model_part}")
    
    # Determine if specific
    if is_exact:
        return True, "exact match"
    elif is_model_part and has_brand and has_model_in_text:
        return True, "model_part + brand + model in text"
    else:
        return False, f"Not specific (is_model_part={is_model_part}, has_brand={has_brand}, has_model_in_text={has_model_in_text})"

# Simulate match for RAM 111 (HyperX Fury)
print("\n--- Checking RAM 111 (Kingston HyperX Fury 16 GB DDR4-3200) ---")
# This would get method like "fuzzy+model_part+freq_exact+capacity_exact"
method_111 = "fuzzy+model_part+freq_exact+capacity_exact"
is_specific_111, reason_111 = check_is_specific_ram(ram_111, normalized, method_111)
print(f"  Method: {method_111}")
print(f"  Is specific: {is_specific_111} ({reason_111})")

# Simulate match for RAM 3289 (HyperX without Fury)
print("\n--- Checking RAM 3289 (Kingston HyperX 16 GB DDR4-4800) ---")
method_3289 = "fuzzy+model_part+freq_mismatch+capacity_exact"
is_specific_3289, reason_3289 = check_is_specific_ram(ram_3289, normalized, method_3289)
print(f"  Method: {method_3289}")
print(f"  Is specific: {is_specific_3289} ({reason_3289})")

print("\n=== Conclusion ===")
if is_specific_111 and not is_specific_3289:
    print("✓ CORRECT: RAM 111 would be selected as specific, RAM 3289 would not")
elif is_specific_3289 and not is_specific_111:
    print("✗ ISSUE: RAM 3289 would be selected but it's missing 'Fury' from the name")
elif is_specific_111 and is_specific_3289:
    print("? Both would be considered specific - higher score wins")
else:
    print("? Neither would be considered specific - fallback would be used")
