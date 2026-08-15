import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

text = """Pārdodu jaudīgu un svaigu gaming pc. Visas detaļas, izņemot videokarti ir 3 mēnešus vecas.

Specifikācijas:

RTX 3070 PNY

I5-12400F

16gb ram ddr4 3200mhz

256GB nvme ssd

700w psu"""

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"Normalized text:\n{text_lower}\n")

# Check positions of PNY and SSD
pny_pos = text_lower.find('pny')
ssd_pos = text_lower.find('ssd')

print(f"'pny' position: {pny_pos}")
print(f"'ssd' position: {ssd_pos}")

# Check segment after PNY
if pny_pos != -1:
    segment = text_lower[pny_pos:pny_pos + 80]
    print(f"\nSegment after 'pny': '{segment}'")
    print(f"Contains 'ssd': {'ssd' in segment}")
    print(f"Contains 'nvme': {'nvme' in segment}")
    print(f"Contains 'm.2': {'m.2' in segment}")
    print(f"Contains 'hdd': {'hdd' in segment}")
