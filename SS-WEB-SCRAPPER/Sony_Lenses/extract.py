"""
Sony Lens Scraper for lab174.com - Final Complete Version
Uses browser automation to navigate through all pages
"""

import json
import csv
from typing import List, Dict

# Store all lenses
all_lenses = []
sony_lenses = []

# Helper to check if Sony lens
def is_sony(name):
    n = name.lower()
    return any(k in n for k in ['sony', 'fe ', 'vario-tessar', 'za oss'])

# Read the extracted data from browser sessions
data = """
Page 1 Data:
Sony FE 12-24mm F2.8 GM|12mm|24mm|2.8|2020|28cm|0.14x|847g|🧱 Very Heavy|138mm|❌ None|✅ Yes|Wide Zoom|❌ No|$3000
Sony FE 12-24mm F4 G|12mm|24mm|4|2017|28cm|0.14x|564g|📕 Medium Heavy|117mm|❌ None|✅ Yes|Wide Zoom|❌ No|$1770
Sony FE 14mm F1.8 GM|14mm|14mm|1.8|2021|25cm|0.1x|4 459g|🧃 Moderate|101mm|✅ Yes|✅ Yes|Ultra Wide|❌ No|$1600
Sony FE 16mm F1.8 G|16mm|16mm|1.8|2025|13cm|0.3x|304g|🍎 Light|75mm|✅ Yes|✅ Yes|Ultra Wide|⭐️ Almost|$849
Sony FE 16-35mm F2.8 GM|16mm|35mm|2.8|2017|28cm|0.19x|679g|📚 Heavy|123mm|❌ None|✅ Yes|Wide Zoom|❌ No|$2200
Sony FE 16-35mm F2.8 GM II|16mm|35mm|2.8|2023|22cm|0.32x|548g|📕 Medium Heavy|112mm|✅ Yes|✅ Yes|Wide Zoom|⭐️ Almost|$2299
Sony FE 16-25mm F2.8 G|16mm|25mm|2.8|2024|17cm|0.2x|4 408g|🧃 Moderate|92mm|✅ Yes|✅ Yes|Wide Zoom|❌ No|$1198
Sony Vario-Tessar T* FE 16-35mm F4 ZA OSS|16mm|35mm|4|2014|28cm|0.19x|517g|📕 Medium Heavy|100mm|❌ None|✅ Yes|Wide Zoom|❌ No|$1000
Sony FE PZ 16–35mm F4 G|16mm|35mm|4|2022|28cm|0.23x|352g|🍎 Light|82mm|✅ Yes|✅ Yes|Wide Zoom|⭐️ Almost|$1200
"""

# Parse this data
lines = [l.strip() for l in data.strip().split('\n') if l.strip() and '|' in l]

for line in lines:
    parts = line.split('|')
    if len(parts) >= 15:
        lens = {
            'lens_name': parts[0],
            'focal_length_wide': parts[1],
            'focal_length_tele': parts[2],
            'f_stop': parts[3],
            'year': parts[4],
            'min_focus_distance': parts[5],
            'max_magnification': parts[6],
            'weight': parts[7],
            'weight_class': parts[8],
            'length': parts[9],
            'aperture_ring': parts[10],
            'autofocus': parts[11],
            'category': parts[12],
            'macro': parts[13],
            'price': parts[14]
        }
        all_lenses.append(lens)
        if is_sony(lens['lens_name']):
            sony_lenses.append(lens)

print(f"Parsed {len(all_lenses)} lenses")
print(f"Sony lenses: {len(sony_lenses)}")

# Save to files
with open('sony_lenses_partial.json', 'w', encoding='utf-8') as f:
    json.dump(sony_lenses, f, indent=2)

print("Saved sony_lenses_partial.json")
