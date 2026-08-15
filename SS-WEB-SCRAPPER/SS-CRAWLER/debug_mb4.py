# -*- coding: utf-8 -*-
# Check the MB context extraction issue

text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Мат. пл. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele."""

lines = text.lower().split('\n')
keywords = ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard', 'мат']

print("Checking each line for MB keywords:")
for i, line in enumerate(lines):
    found = []
    for kw in keywords:
        if kw in line:
            found.append(kw)
    if found:
        print(f"Line {i}: '{line}'")
        print(f"  Found keywords: {found}")
    
# Check if 'мат' is even in the text
print("\n" + "="*60)
print("Checking raw characters:")
line_with_mb = lines[2]  # The Мат. пл. line
print(f"Line 2 repr: {repr(line_with_mb)}")

# Check if 'мат' matches
print(f"\n'mat' in line: {'мат' in line_with_mb}")
print(f"'мат' (cyrillic) in line: {'мат' in line_with_mb}")

# Compare ASCII vs Cyrillic
ascii_mat = 'мат'  # This is what I type on my keyboard
print(f"\nASCII 'мат' repr: {repr(ascii_mat)}")

# Check if they match
line_bytes = line_with_mb.encode('utf-8')
ascii_bytes = ascii_mat.encode('utf-8')
print(f"Line bytes: {line_bytes[:20]}")
print(f"ASCII bytes: {ascii_bytes}")
print(f"Match: {ascii_mat in line_with_mb}")
