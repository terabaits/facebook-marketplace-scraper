# -*- coding: utf-8 -*-
"""Debug actual listing text from web fetch."""
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

# This is the actual text from the web fetch
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

print("=== Actual Listing Text Analysis ===")
print(f"Normalized: {normalized}")
print()

# Check for key terms
print("=== Key Terms in Normalized Text ===")
terms = ['hyperx', 'fury', 'kingston', 'asus', 'tuf', 'b450', 'plus', 'gaming', 'b450-plus', 'b450plus']
for term in terms:
    print(f"  '{term}' in normalized: {term in normalized}")
print()

# Check for motherboard context
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

print(f"MB Context: {mb_context}")
print()

# Check RAM matching
print("=== RAM Analysis ===")
ram_111_name = 'kingston hyperx fury 16 gb'
ram_3289_name = 'kingston hyperx 16 gb'

print(f"RAM 111 name normalized: '{ram_111_name}'")
print(f"RAM 3289 name normalized: '{ram_3289_name}'")
print(f"RAM 111 in normalized: {ram_111_name in normalized}")
print(f"RAM 3289 in normalized: {ram_3289_name in normalized}")

# Check if HyperX Fury is mentioned
print(f"\n'hyperx' in normalized: {'hyperx' in normalized}")
print(f"'fury' in normalized: {'fury' in normalized}")

# Check for motherboard matching
print("\n=== Motherboard Analysis ===")
mb_plus_name = 'asus tuf b450 plus gaming'
mb_pro_name = 'asus tuf b450 pro gaming'

print(f"MB PLUS name normalized: '{mb_plus_name}'")
print(f"MB PRO name normalized: '{mb_pro_name}'")
print(f"MB PLUS in mb_context: {mb_plus_name in mb_context}")
print(f"MB PRO in mb_context: {mb_pro_name in mb_context}")

# Check if Asus/TUF/B450-plus is mentioned
print(f"\n'asus' in mb_context: {'asus' in mb_context}")
print(f"'tuf' in mb_context: {'tuf' in mb_context}")
print(f"'b450-plus' in normalized: {'b450-plus' in normalized}")
print(f"'b450plus' in normalized: {'b450plus' in normalized}")

# The actual text has "Motherboars Asus Tuf B450-plus gaming"
# After normalization: "motherboars asus tuf b450plus gaming"
print(f"\n'motherboars asus tuf b450plus gaming' in normalized: {'motherboars asus tuf b450plus gaming' in normalized}")
print(f"'asus tuf b450plus gaming' in normalized: {'asus tuf b450plus gaming' in normalized}")
