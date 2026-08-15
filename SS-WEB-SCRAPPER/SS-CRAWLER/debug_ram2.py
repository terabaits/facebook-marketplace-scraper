# -*- coding: utf-8 -*-
import re

text_lower = """itel core i59400f coffee lake 2.90 ghz mat. pl. gigabyte h310m s2h 2.0 gskill ddr42666 32gb gigabyte nvidia geforce gtx 1660 6gb ddr5 sdd 512gb hdd 500gb windows 10 monitor aoc 25 lcd 2590g4 riga jelgava dobele.

 procesors:

 intel core i5

 procesora frekvence, ghz:

 2.90

 pamat plate:

 gigabyt h310m

 video:

 nvidia 1660 6gb

 operativa atmina, gb:

 32

 hdd apjoms, gb:

 512

 dvd:

 -

 stavoklis:

 lietota

 cena:

 550 e

 foto:

\thttps://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859882.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859883.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859884.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859885.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859886.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859887.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859888.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859889.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859890.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859891.800.jpg

 talrunis:

 (+371)29-97-***

 visi sludinajumi ar so talruni

\te-mail:
\tnosutit e-pastuvisi sludinajumi ar so e-mail adresi

vieta:dobele un raj.

pievienot memo

\tizdrukat
\tdatums: 10.05.2026 18:56

\t[parsutit sludinajumu](mailto:?body=https%3a%2f%2fwww.ss.com%2fmsg%2flv%2felectronics%2fcomputers%2fpc%2faacph.html%0d%0a%0d%0a&subject=sludinajums%20no%20ss.com)

\tunikalo apmeklejumu skaits: 1

 atgadinat

 pazinot par parkapumu"""

# Pattern 0: "4x8GB" or "4 x 8GB" or "4x 8GB" format - calculate total FIRST
multi_stick_patterns = [
    r'(\d+)\s*x\s*(\d+)\s*gb',             # "4x8GB" or "4 x 8GB"
    r'(\d+)\s*(?:x|×)\s*(\d+)\s*gb',       # "4×8GB" with times symbol
    r'(\d+)x\s*(\d+)\s*gb',                 # "4x 8GB" (no space after x)
]

print("Testing multi-stick patterns:")
for pattern in multi_stick_patterns:
    matches = re.findall(pattern, text_lower)
    if matches:
        for match in matches:
            sticks = int(match[0])
            capacity_per_stick = int(match[1])
            total = sticks * capacity_per_stick
            print(f"  Found: {sticks}x{capacity_per_stick}GB = {total}GB")

# Check for the actual extraction pattern from the code
# Pattern: Look for lines with RAM keywords
lines = text_lower.split('\n')
ram_lines = []
for line in lines:
    if any(kw in line for kw in ['operativ', 'ram', 'atmiņ', 'ddr', 'memory', 'pam']):
        ram_lines.append(line)

print(f"\nRAM-related lines: {len(ram_lines)}")
for line in ram_lines:
    print(f"  '{line[:80]}'")

ram_text = ' '.join(ram_lines) if ram_lines else text_lower

# Pattern: "DDR" + capacity
ddr_patterns = [
    r'ddr\d?\s*[-]?\s*(\d+)\s*gb',
    r'ddr\d?[^a-zA-Z]{0,20}(\d+)\s*gb',
    r'(\d+)\s*gb[^a-zA-Z]{0,20}ddr',
]

print("\nTesting DDR patterns:")
for pattern in ddr_patterns:
    matches = re.findall(pattern, ram_text)
    if matches:
        print(f"  Pattern '{pattern}' found: {matches}")

# Fallback: generic X GB pattern (filter out GPU VRAM and SSD/HDD)
gb_matches = list(re.finditer(r'\b(\d+)\s*gb\b', text_lower))
print(f"\nAll GB matches found: {len(gb_matches)}")
for match in gb_matches:
    # Get smaller context around the match
    start = max(0, match.start() - 20)
    end = min(len(text_lower), match.end() + 20)
    context = text_lower[start:end]
    
    # Skip GPU VRAM - look for GPU patterns close to the number
    gpu_patterns = [
        r'gtx\s*\d+\s*gb',
        r'rtx\s*\d+\s*gb',
        r'rx\s*\d+\s*gb',
        r'geforce.*?\d+\s*gb',
        r'radeon.*?\d+\s*gb',
        r'gpu.*?\d+\s*gb',
        r'vram.*?\d+\s*gb',
        r'\d+\s*gb\s*vram',
        r'\d+\s*gb\s*gpu',
    ]
    is_gpu = any(re.search(pattern, context) for pattern in gpu_patterns)
    
    # Skip SSD/HDD storage - look for storage patterns
    storage_patterns = [
        r'ssd.*?\d+\s*gb',
        r'hdd.*?\d+\s*gb',
        r'nvme.*?\d+\s*gb',
        r'm\.2.*?\d+\s*gb',
        r'disk.*?\d+\s*gb',
        r'\d+\s*gb\s*ssd',
        r'\d+\s*gb\s*hdd',
        r'\d+\s*gb\s*nvme',
    ]
    is_storage = any(re.search(pattern, context) for pattern in storage_patterns)
    
    print(f"  Match: {match.group(0)} at pos {match.start()}")
    print(f"    Context: '{context}'")
    print(f"    Is GPU: {is_gpu}, Is Storage: {is_storage}")
    if not is_gpu and not is_storage:
        print(f"    ** This would be returned as RAM capacity: {match.group(1)}GB")
