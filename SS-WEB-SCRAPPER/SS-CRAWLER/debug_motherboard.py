import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

import re
from src.utils.text import normalize_text

# Test text
text = "Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)\n\nПолностью рабочий компьютер, подходит для игр и повседневных задач.\n\nПроцессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)\n\nВидеокарта: Nvidia GeForce GTX 1650 (4GB)\n\nОперативная память: 16GB DDR4 3200 MHz\n\nSSD: 1TB Kingston NV1\n\nHDD: 2TB Seagate\n\nБлок питания: 650W\n\n Procesors:\n\n Intel Core i5\n\n Procesora frekvence, Ghz:\n\n 2.60\n\n Pamat plate:\n\n Gigabyte H510M H\n\n Video:\n\n Nvidia geforce gtx 1650\n\n Operatīvā atmiņa, Gb:\n\n 16\n\n HDD apjoms, Gb:\n\n 2000\n\n DVD:\n\n -\n\n Stāvoklis:\n\n lietota\n\n Cena:\n\n 300 €"

normalized = normalize_text(text)
print(f"Normalized text:\n{normalized}\n")

# Check for motherboard lines
for line in text.lower().split('\n'):
    if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']):
        print(f"MB line: {line}")
        print(f"  Normalized: {normalize_text(line)}")

# Check normalized text for H510M
if 'h510m' in normalized:
    print("\n'h510m' found in normalized text")
else:
    print("\n'h510m' NOT found in normalized text")
    print("Looking for similar patterns:")
    import re
    matches = re.findall(r'h\d+m?', normalized)
    if matches:
        print(f"  Found: {matches}")
