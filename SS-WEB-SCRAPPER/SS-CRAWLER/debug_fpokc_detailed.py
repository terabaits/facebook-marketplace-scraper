# -*- coding: utf-8 -*-
"""Debug fpokc in detail."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

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

print("=== GPU Pattern Removal Check ===")

# Simulate GPU matcher CPU removal patterns
cpu_patterns = [
    r'i[3579]\s*-?\s*\d{4,5}',  # Intel Core i3/i5/i7/i9
    r'ryzen\s*\d?\s*\d{3,4}',     # AMD Ryzen
    r'r[3579]\s*\d{3,4}',          # Ryzen shorthand R5/R7/R9
    r'xeon\s*[ew]?\d*-?\d{4}',     # Intel Xeon
]

text_lower = text.lower()
print(f"Original: {text_lower[:100]}...")

text_for_gpu = text_lower
for pattern in cpu_patterns:
    text_for_gpu = re.sub(pattern, '', text_for_gpu, flags=re.IGNORECASE)
    
text_for_gpu = re.sub(r'\s+', ' ', text_for_gpu).strip()
print(f"\nAfter CPU removal: {text_for_gpu[:100]}...")

# Check if "760" is still there
if '760' in text_for_gpu:
    print("  '760' found in text - will match GTX 760")
else:
    print("  '760' removed - good!")

print("\n=== SSD Brand Near Check ===")

# Check if "crucial" appears
if 'crucial' in text_lower:
    print("'crucial' found in text")
    crucial_pos = text_lower.find('crucial')
    # Check window
    window_start = max(0, crucial_pos - 40)
    window_end = min(len(text_lower), crucial_pos + 40)
    window = text_lower[window_start:window_end]
    print(f"  Window [{window_start}:{window_end}]: '{window}'")
    has_ssd = any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2'])
    print(f"  Has SSD kw in window: {has_ssd}")

# Check if "gigabyte" appears
if 'gigabyte' in text_lower:
    print("\n'gigabyte' found in text")
    gig_pos = text_lower.find('gigabyte')
    # Check window
    window_start = max(0, gig_pos - 40)
    window_end = min(len(text_lower), gig_pos + 40)
    window = text_lower[window_start:window_end]
    print(f"  Window [{window_start}:{window_end}]: '{window}'")
    has_ssd = any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2'])
    print(f"  Has SSD kw in window: {has_ssd}")
