import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# Text from the listing
text = """Pārdodu jaudīgu un svaigu gaming pc. Visas detaļas, izņemot videokarti ir 3 mēnešus vecas.

Specifikācijas:

RTX 3070 PNY

I5-12400F

16gb ram ddr4 3200mhz

256GB nvme ssd

700w psu

Atrodas Rīgā, Purvciemā. Var sarunāt piegādi."""

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"Normalized text:\n{normalized}\n")

# Check if teamgroup or cs1030 is in the text
print(f"'teamgroup' in text: {'teamgroup' in text_lower}")
print(f"'cs1030' in text: {'cs1030' in text_lower}")
print(f"'team' in text: {'team' in text_lower}")
print(f"'group' in text: {'group' in text_lower}")

# Check SSD-related context
ssd_lines = []
for line in text_lower.split('\n'):
    if any(kw in line for kw in ['ssd', 'nvme', 'm.2', 'hdd', 'disk', 'atmiņ', 'storage']):
        ssd_lines.append(line)

print(f"\nSSD-related lines:")
for line in ssd_lines:
    print(f"  {line}")
