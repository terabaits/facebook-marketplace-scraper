# -*- coding: utf-8 -*-
"""Test the fixed matching logic for alnnx listing."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER\\src')

import re

def normalize_text(text):
    """Normalize text for search matching."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# The actual text from the listing
text = """Pc-Dators.

Ryzen 5 1600x.

Ddr4 16gb Hyperx.

Motherboars Asus Tuf B450-plus gaming.

Ssd 128gb samsung(Windows), Hdd 1Tb wd blue.

Gigabyte Gtx 1060 3GB.

Ir rgb.

Bez defektiem.

Iespejams pārbaudīt uz vietas.

Iespējams sarunāt piegādi.

 Procesors:

 Ryzen 5 1600x

 Procesora frekvence, Ghz:

 4

 Pamat plate:

 B450

 Video:

 Gtx 1060

 Operatīvā atmiņa, Gb:

 16

 HDD apjoms, Gb:

 1000

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 230 €"""

normalized = normalize_text(text)

print("=== Testing Fixed Logic ===")
print(f"Normalized: {normalized}")
print()

# Test RAM matching logic (simulating the fixed code)
print("=== RAM Matching (Fixed Logic) ===")

# Simulate a RAM match result
ram_match = {
    'name': 'Kingston HyperX Fury 16 GB',
    'method': 'fuzzy+model_part+freq_exact+capacity_exact'
}

ram_name_lower = ram_match['name'].lower()
brand = ram_name_lower.split()[0] if ram_name_lower else ""

# Check if brand is in text
brand_norm = brand.replace('.', '')
has_brand = brand in normalized or brand_norm in normalized

# Special handling: HyperX is Kingston's gaming brand
if not has_brand and 'hyperx' in ram_name_lower and 'hyperx' in normalized:
    has_brand = True
    print("  Applied: HyperX special brand handling")

# Check for model series keyword
model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                  'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                  't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                  'viper', 'steel', 'patriot', 'hyperx', 'aegis']
has_model_in_text = False
for kw in model_keywords:
    if kw in ram_name_lower and kw in normalized:
        has_model_in_text = True
        print(f"  Found model keyword: {kw}")
        break

# Special handling: If "hyperx" is in text and the RAM is a HyperX model
if not has_model_in_text and 'hyperx' in ram_name_lower and 'hyperx' in normalized:
    has_model_in_text = True
    print("  Applied: HyperX model special handling")

print(f"  Brand: '{brand}'")
print(f"  has_brand: {has_brand}")
print(f"  has_model_in_text: {has_model_in_text}")

is_exact = ram_match['method'].split('+')[0] == 'exact'
is_model_part = 'model_part' in ram_match['method']

is_specific_ram = False
if is_exact:
    is_specific_ram = True
    reason = "exact match"
elif is_model_part and has_brand and has_model_in_text:
    is_specific_ram = True
    reason = "model_part + brand + model"
else:
    reason = f"not specific (exact={is_exact}, model_part={is_model_part}, has_brand={has_brand}, has_model={has_model_in_text})"

print(f"  is_specific_ram: {is_specific_ram} ({reason})")
print()

# Test Motherboard matching logic
print("=== Motherboard Matching (Fixed Logic) ===")

# Build brand_model_names with hyphen-less variants
def build_mb_index(mbs):
    brand_model_names = {}
    for mb in mbs:
        norm = normalize_text(f"{mb['brand']} {mb['model']}")
        brand_model_names[norm] = mb
        
        # Also add variant without hyphens
        model_no_hyphens = mb['model'].replace('-', '').replace(' ', '')
        norm_no_hyphens = normalize_text(f"{mb['brand']} {model_no_hyphens}")
        if norm_no_hyphens not in brand_model_names:
            brand_model_names[norm_no_hyphens] = mb
            print(f"  Added hyphen-less variant: '{norm_no_hyphens}'")
    return brand_model_names

mbs = [
    {'id': 7446, 'brand': 'Asus', 'model': 'TUF B450-PLUS GAMING', 'chipset': 'B450'},
    {'id': 7447, 'brand': 'Asus', 'model': 'TUF B450-PRO GAMING', 'chipset': 'B450'},
]

brand_model_names = build_mb_index(mbs)

# Check for exact match
lines = text.lower().split('\n')
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

print(f"\n  MB Context: '{mb_context}'")

# Check for exact matches
sorted_names = sorted(brand_model_names.items(), key=lambda x: len(x[0]), reverse=True)
matched_mb = None
for name, mb in sorted_names:
    if name in normalized:  # Check in full normalized text, not just mb_context
        print(f"  EXACT MATCH: '{name}' -> ID {mb['id']}: {mb['brand']} {mb['model']}")
        matched_mb = mb
        break

if matched_mb:
    print(f"\n  ✓ Would match ID {matched_mb['id']}: {matched_mb['brand']} {matched_mb['model']}")
else:
    print("\n  No exact match found in normalized text")
