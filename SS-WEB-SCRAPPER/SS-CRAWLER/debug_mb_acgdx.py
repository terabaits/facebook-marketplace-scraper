# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    mbs = MotherboardRepository.get_all(session)

matcher = MotherboardMatcher(mbs)

# Full acgdx description
desc = """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)
Полностью рабочий компьютер, подходит для игр и повседневных задач.
Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)
Видеокарта: Nvidia GeForce GTX 1650 (4GB)
Оперативная память: 16GB DDR4 3200 MHz
SSD: 1TB Kingston NV1
HDD: 2TB Seagate
Блок питания: 650W
procesors:intel core i5procesora frekvence, ghz:2.60pamat plate:gigabyte h510m hvideo:nvidia geforce gtx 1650operatīvā atmiņa, gb:16hdd apjoms, gb:2000dvd:-stāvoklis:lietota: Procesors:
procesors:: Intel Core i5
procesora frekvence, ghz:: 2.60
pamat plate:: Gigabyte H510M H
video:: Nvidia geforce gtx 1650
operatīvā atmiņa, gb:: 16
hdd apjoms, gb:: 2000
dvd:: -
stāvoklis:: lietota"""

normalized = normalize_text(desc)
print("Testing acgdx motherboard matching...")
print(f"Full normalized text:\n{normalized}\n")

print(f"'h510m' in normalized: {'h510m' in normalized}")
print(f"'h510' in normalized: {'h510' in normalized}")
print(f"'gigabyte' in normalized: {'gigabyte' in normalized}")

# Check motherboard match
result = matcher.match(desc, "")
print(f"\nMatch result: {result.motherboard}")
if result.motherboard:
    print(f"  ID: {result.motherboard.id}")
    print(f"  Brand: {result.motherboard.brand}")
    print(f"  Model: {result.motherboard.model}")
    print(f"  Method: {result.method}")
else:
    print("  No match found")
