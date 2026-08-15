# -*- coding: utf-8 -*-
import re

text = """Itel Core i5-9400f Coffee Lake 2.90 Ghz

Mat. pl. Gigabyte H310M S2H 2.0

G. Skill Ddr4-2666 32gb

Gigabyte Nvidia GeForce GTX 1660 6gb DDR5

SDD 512gb HDD 500gb

Windows 10

Monitor: AOC 25" LCD 2590G4

Riga, Jelgava, Dobele.

 Procesors:

 Intel Core i5

 Procesora frekvence, Ghz:

 2.90

 Pamat plate:

 Gigabyt h310m

 Video:

 Nvidia 1660 6gb

 Operatīvā atmiņa, Gb:

 32

 HDD apjoms, Gb:

 512

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 550 €

 Foto:

	https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859882.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859883.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859884.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859885.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859886.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859887.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859888.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859889.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859890.800.jpg

https://i.ss.com/gallery/8/1458/364300/electronics-computers-pc-72859891.800.jpg

 Tālrunis:

 (+371)29-97-***

 Visi sludinājumi ar šo tālruni

	E-mail:
	Nosūtīt e-pastuVisi sludinājumi ar šo E-mail adresi

Vieta:Dobele un raj.

Pievienot Memo

	Izdrukāt
	Datums: 10.05.2026 18:56

	[Pārsūtīt sludinājumu](mailto:?body=https%3A%2F%2Fwww.ss.com%2Fmsg%2Flv%2Felectronics%2Fcomputers%2Fpc%2Faacph.html%0D%0A%0D%0A&subject=Sludinajums%20no%20SS.COM)

	Unikālo apmeklējumu skaits: 1

 Atgādināt

 Paziņot par pārkāpumu"""

text_lower = text.lower()

# Pattern 0: "4x8GB" or "4 x 8GB" or "4x 8GB" format - calculate total FIRST
# This pattern is most reliable for multi-stick RAM configs
multi_stick_patterns = [
    r'(\d+)\s*x\s*(\d+)\s*gb',             # "4x8GB" or "4 x 8GB"
    r'(\d+)\s*(?:x|×)\s*(\d+)\s*gb',       # "4×8GB" with times symbol
    r'(\d+)x\s*(\d+)\s*gb',                 # "4x 8GB" (no space after x)
    r'(\d+)\s*planks?.*?\d+\s*gb',          # "4 planks ... 8GB"
    r'(\d+)\s*(?:planki|plank|plashki|planku|modules?|sticks?).*?(\d+)\s*gb',  # "4 planki/plashki ... 8GB"
    r'(\d+)x.*?\b(\d+)\s*gb',               # "4x ... 8GB" with word boundary
]

print("Testing multi-stick patterns:")
for pattern in multi_stick_patterns:
    match = re.search(pattern, text_lower)
    if match:
        try:
            sticks = int(match.group(1))
            capacity_per_stick = int(match.group(2))
            total = sticks * capacity_per_stick
            print(f"  Pattern matched: {match.group(0)} -> {total}GB")
        except ValueError:
            pass

# Pattern 1: Look for RAM-related lines first
lines = text_lower.split('\n')
ram_lines = []
for line in lines:
    if any(kw in line for kw in ['operativ', 'ram', 'atmiņ', 'ddr', 'memory', 'pam']):
        ram_lines.append(line)

print(f"\nRAM-related lines found: {len(ram_lines)}")
for line in ram_lines:
    print(f"  '{line}'")

ram_text = ' '.join(ram_lines) if ram_lines else text_lower
print(f"\nRAM text: '{ram_text[:100]}...'")

# Pattern 3: Latvian format - "Operativā atmiņa, Gb: 16" or "Gb: 16"
latvian_patterns = [
    r'gb\s*:?\s*(\d+)',  # Gb: 16
    r'atmina\s*,?\s*gb\s*:?\s*(\d+)',  # atmina, Gb: 16 (normalized)
    r'operativa\s+atmina.*?(\d+)\s*gb',  # operativa atmina...16 gb (normalized)
]

print("\nTesting Latvian patterns:")
for pattern in latvian_patterns:
    match = re.search(pattern, ram_text)
    if match:
        print(f"  Pattern '{pattern}' matched: {match.group(0)} -> {match.group(1)}GB")
