import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    mbs = MotherboardRepository.get_all(session)

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

normalized = normalize_text(text)
print(f"Normalized text:\n{normalized}\n")

# Check if H510M is in the text
if 'h510m' in normalized:
    print("'h510m' found in normalized text")
else:
    print("'h510m' NOT found in normalized text")
    
# Check for H510M in database
print("\nSearching for H510M motherboards:")
for mb in mbs:
    if 'h510' in mb.model.lower():
        print(f"  ID {mb.id}: {mb.brand} {mb.model}")
        norm_name = normalize_text(f"{mb.brand} {mb.model}")
        print(f"    Normalized: '{norm_name}'")
        print(f"    In text: {norm_name in normalized}")

# Check for Gigabyte H
print("\nSearching for 'Gigabyte H' motherboards:")
for mb in mbs:
    norm_name = normalize_text(f"{mb.brand} {mb.model}")
    if norm_name == 'gigabyte h':
        print(f"  ID {mb.id}: {mb.brand} {mb.model}")
        print(f"    Socket: {mb.socket}, Chipset: {mb.chipset}")
