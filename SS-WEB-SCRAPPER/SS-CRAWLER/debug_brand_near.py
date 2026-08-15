# -*- coding: utf-8 -*-
"""Debug brand_near_ssd logic in detail."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
import re

# fpokc full text
text = """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini
Dators ir pilnībā darba kārtībā.
Cena 500 EUR.
Rīga"""

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"Full normalized text:\n{normalized}\n")

# Simulate brand_near_ssd logic
ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata', 'sandisk', 'seagate', 'teamgroup', 'pny', 'netac']

print("=== Checking brand_near_ssd ===")
brand_near_ssd = False
ssd_context = text_lower

# First check: SSD keyword anywhere in text with brand nearby (±40 chars)
print("\nFirst check (window ±40 chars):")
for brand in ssd_brand_keywords:
    if brand in text_lower:
        brand_pos = text_lower.find(brand)
        window_start = max(0, brand_pos - 40)
        window_end = min(len(text_lower), brand_pos + 40)
        window = text_lower[window_start:window_end]
        has_ssd_kw = any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2', 'solid'])
        print(f"  Brand '{brand}' at pos {brand_pos}")
        print(f"    Window [{window_start}:{window_end}]: '{window[:60]}...'")
        print(f"    Has SSD kw: {has_ssd_kw}")
        if has_ssd_kw:
            brand_near_ssd = True
            ssd_context = window
            break

print(f"\nFirst check result: brand_near_ssd = {brand_near_ssd}")

# Second check: brand before capacity
if not brand_near_ssd:
    print("\nSecond check (brand before capacity):")
    for brand in ssd_brand_keywords:
        if brand in text_lower:
            brand_pos = text_lower.find(brand)
            segment_after = text_lower[brand_pos:brand_pos + 30]
            cap_match = re.search(r'(\d+)\s*(?:gb|tb)', text_lower)
            if cap_match:
                cap_pos = cap_match.start()
                print(f"  Brand '{brand}' at {brand_pos}, capacity at {cap_pos}")
                print(f"    Brand before capacity: {brand_pos < cap_pos}")
                if brand_pos < cap_pos:
                    segment_around_cap = text_lower[cap_pos:cap_pos + 20]
                    has_ssd_kw = any(kw in segment_around_cap for kw in ['ssd', 'nvme', 'm.2'])
                    print(f"    SSD kw after capacity: {has_ssd_kw}")
                    if has_ssd_kw:
                        brand_near_ssd = True
                        break

print(f"\nFinal result: brand_near_ssd = {brand_near_ssd}")
