# -*- coding: utf-8 -*-
"""Debug eiklm GPU detection."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# eiklm text
text = """Pārdod spēļu datoru.
Procesors: Ryzen 7 5800X3D
Mātesplate: Gigabyte B450 Aorus Elite
Operatīvā atmiņa: DDR4 Kingston FURY Renegade 32GB 3600MHz
Cietie diski: SSD Kingston Renegade G5 1TB + HDD Seagate Barracuda 2TB
Video karte: Bez videokartes
Barošanas bloks: Corsair CS850M 850W
Korpuss: Deepcool"""

normalized = normalize_text(text)
text_lower = normalized.lower()

print("=== eiklm GPU Detection Debug ===")
print(f"Normalized text:\n{normalized}\n")

# Check has_no_gpu patterns
has_no_gpu_patterns = ['video nav', 'nav video', 'no gpu', 'gpu nav', 
                       'bez videokartes', 'bez video', 'nav videokarte',
                       'bez gpu', 'nav gpu']

print("Checking has_no_gpu patterns:")
for pattern in has_no_gpu_patterns:
    if pattern in text_lower:
        print(f"  FOUND: '{pattern}'")

# Check has_gpu_option
has_gpu_option = 'videokarte' in text_lower or 'video' in text_lower
print(f"\nhas_gpu_option ('videokarte' or 'video' in text): {has_gpu_option}")

# Check integrated graphics
integrated_patterns = [
    r'intel\s+(?:uhd|hd|xe)\s+graphics',
    r'intel\s+graphics\s+\d+',
    r'amd\s+vega\s+\d+',
    r'amd\s+radeon\s+vega',
]

print("\nChecking integrated graphics patterns:")
import re
for pattern in integrated_patterns:
    match = re.search(pattern, text_lower)
    print(f"  Pattern '{pattern[:30]}': {match is not None}")

# Final condition
has_no_gpu = any(kw in text_lower for kw in has_no_gpu_patterns)
print(f"\nhas_no_gpu: {has_no_gpu}")
print(f"has_gpu_option: {has_gpu_option}")
print(f"Should skip GPU matching: {has_no_gpu and not has_gpu_option}")
