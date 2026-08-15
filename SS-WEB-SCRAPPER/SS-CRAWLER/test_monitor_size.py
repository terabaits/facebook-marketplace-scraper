import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Test text
text = """Pārdodu PC

Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng"""

text_lower = text.lower()

# Find monitor-related sections
monitor_sections = []

# Look for sections mentioning "monitor" or "ekrans" (Latvian)
monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays']
lines = text_lower.split('\n')

for line in lines:
    line_lower = line.lower()
    # Check if line mentions monitor
    if any(kw in line_lower for kw in monitor_keywords):
        monitor_sections.append(line_lower)

print("Lines with monitor keywords:")
for section in monitor_sections:
    print(f"  '{section}'")

# Search in monitor sections first
search_text = ' '.join(monitor_sections) if monitor_sections else text_lower
print(f"\nSearch text: '{search_text}'")

# Match patterns like "24", "24\"", "24 inch", "27.5"
size_patterns = [
    r'(\d{2,3}(?:\.\d)?)\s*["\']\s*(?:inch|in)?',  # 24" or 24'
    r'(\d{2,3})\s*(?:inch|in|″)',  # 24 inch or 24″
    r'\bmonitor\w*\s+(\d{2,3})',  # "monitor 24" or "monitorā 27"
    r'ekrans\w*\s+(\d{2,3})',  # Latvian
    r'\+\s*(?:monitor|ekrans)?\s*[:\-]?\s*(\d{2,3})',  # + monitor 24
]

print("\nTrying patterns:")
for pattern in size_patterns:
    match = re.search(pattern, search_text)
    if match:
        print(f"  Pattern matched: {pattern}")
        print(f"    Match: '{match.group()}'")
        size = match.group(1)
        print(f"    Size: '{size}'")
        try:
            size_num = float(size)
            if 21 <= size_num <= 49:
                print(f"    -> VALID: {int(size_num)}")
            else:
                print(f"    -> INVALID: {size_num} not in range 21-49")
        except ValueError:
            print(f"    -> ERROR parsing '{size}'")
    else:
        print(f"  Pattern NOT matched: {pattern[:50]}...")
