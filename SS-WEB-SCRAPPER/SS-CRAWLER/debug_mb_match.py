import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

import psycopg2
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.models.schemas import MotherboardReference

# Connect to database and load motherboards
conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Load motherboards
mb_list = []
cur.execute("SELECT id, brand, model, chipset, socket FROM motherboard_reference")
for row in cur.fetchall():
    mb_list.append(MotherboardReference(
        id=row[0], brand=row[1], model=row[2], chipset=row[3], socket=row[4]
    ))

cur.close()
conn.close()

# Initialize matcher
matcher = MotherboardMatcher(mb_list)

# Test text
text = """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)

Полностью рабочий компьютер, подходит для игр и повседневных задач.

Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)

Видеокарта: Nvidia GeForce GTX 1650 (4GB)

Оперативная память: 16GB DDR4 3200 MHz

SSD: 1TB Kingston NV1

HDD: 2TB Seagate

Блок питания: 650W

 Procesors:

 Intel Core i5

 Procesora frekvence, Ghz:

 2.60

 Pamat plate:

 Gigabyte H510M H

 Video:

 Nvidia geforce gtx 1650

 Operatīvā atmiņa, Gb:

 16

 HDD apjoms, Gb:

 2000

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 300 €"""

# Get mb_context
lines = text.lower().split('\n')
mb_context_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        mb_context_lines.append(line)
        skip_next = False
        continue
    if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']):
        mb_context_lines.append(line)
        if i + 1 < len(lines):
            mb_context_lines.append(lines[i + 1])
            skip_next = True

print("MB context lines:")
for line in mb_context_lines:
    print(f"  '{line}'")

from src.utils.text import normalize_text
mb_context = ' '.join(mb_context_lines)
print(f"\nMB context: '{mb_context}'")
print(f"Normalized MB context: '{normalize_text(mb_context)}'")

# Check if H510M is in the index
print("\nChecking brand_model_names for H510M:")
for name, mb in matcher.brand_model_names.items():
    if 'h510m' in name or 'h510' in name:
        print(f"  '{name}' -> ID {mb.id}: {mb.brand} {mb.model}")
