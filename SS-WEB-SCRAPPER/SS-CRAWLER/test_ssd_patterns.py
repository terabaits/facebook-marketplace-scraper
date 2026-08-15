import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import re

# Test the exact text pattern from the listing
text = """Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb"""

text_lower = text.lower()
print("Testing SSD patterns on actual listing text:")
print("="*50)

# Pattern 1: "128GB SSD"
pattern1 = list(re.finditer(r'(\d{3,4})\s*gb\s+(?:ssd|nvme|m\.2)', text_lower))
print(f"Pattern 1 (XXXgb ssd): {len(pattern1)} matches")
for m in pattern1:
    print(f"  {m.group(1)}GB at pos {m.start()}")

# Pattern 2: "SSD 128GB"  
pattern2 = list(re.finditer(r'(?:ssd|nvme|m\.2)\s+(\d{3,4})\s*gb', text_lower))
print(f"Pattern 2 (ssd XXXgb): {len(pattern2)} matches")
for m in pattern2:
    print(f"  {m.group(1)}GB at pos {m.start()}")

# Combined unique mentions
ssd_mentions = []
for m in pattern1:
    capacity = int(m.group(1))
    ssd_mentions.append((capacity, m.start()))
for m in pattern2:
    capacity = int(m.group(1))
    ssd_mentions.append((capacity, m.start()))

# Remove duplicates
unique = []
seen = set()
for cap, pos in ssd_mentions:
    if pos not in seen:
        seen.add(pos)
        unique.append((cap, pos))

print(f"\nUnique SSD mentions: {len(unique)}")
for cap, pos in unique:
    print(f"  {cap}GB at position {pos}")

if len(unique) > 1:
    print(f"\nPrimary SSD: {unique[0][0]}GB")
    print(f"Additional SSDs: {[cap for cap, pos in unique[1:]]}")
else:
    print("\nOnly 1 SSD detected!")
