# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# alnnx text from CLI
alnnx_text = """Pārdod spēļu datoru. Procesors: AMD Ryzen 5 1600X 3.6GHz, Mātesplate: Asus TUF B450-PLUS GAMING,
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz, Cietie diski: SSD 128GB + HDD 1TB,
Video karte: GTX 1060 3GB, Barošanas bloks: 500W, Korpuss: Fractal Design"""

fcddo_text = """Pārdod datoru. Procesors: Intel Core i5-4460, Mātesplate: MSI H81M Eco,
Operatīvā atmiņa: DDR3 16GB, Video karte: GTX 1060 3GB, Cietie diski: SSD 500GB Crucial P1"""

fkffx_text = """Pārdod datoru. Procesors: Intel Core i7-6700, Operatīvā atmiņa: DDR4 16GB,
Cietie diski: SSD 240GB, Video karte: Bez videokartes"""

print("=== alnnx normalized ===")
print(normalize_text(alnnx_text))

print("\n=== fcddo normalized ===")
print(normalize_text(fcddo_text))

print("\n=== fkffx normalized ===")
print(normalize_text(fkffx_text))

print("\n=== Check for 'hyperx' in alnnx ===")
norm = normalize_text(alnnx_text)
print(f"'hyperx' in normalized: {'hyperx' in norm}")
print(f"'fury' in normalized: {'fury' in norm}")

print("\n=== Check for 'i54460' in fcddo ===")
norm = normalize_text(fcddo_text)
print(f"'i54460' in normalized: {'i54460' in norm}")
print(f"'i54460s' in normalized: {'i54460s' in norm}")
