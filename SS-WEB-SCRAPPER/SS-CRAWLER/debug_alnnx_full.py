# -*- coding: utf-8 -*-
"""Debug alnnx full matching."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository,
    MotherboardRepository, MonitorRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cm = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSURepository.get_all(session),
        cases=CaseRepository.get_all(session),
        motherboards=MotherboardRepository.get_all(session),
        monitors=MonitorRepository.get_all(session)
    )

# alnnx full text
text = """Pārdod spēļu datoru.
Procesors: AMD Ryzen 5 1600X 3.6GHz
Mātesplate: Asus TUF B450-PLUS GAMING
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz
Cietie diski: SSD 128GB + HDD 1TB
Video karte: GTX 1060 3GB
Barošanas bloks: 500W
Korpuss: Fractal Design"""

print("=== alnnx Full Debug ===")
normalized = normalize_text(text)
print(f"Full normalized:\n{normalized}\n")

result = cm.match("Test", text, 230.0)

print(f"CPU: {result.cpu.get('cpu_name') if result.cpu else 'None'}")
print(f"GPU: {result.gpu.get('model') if result.gpu else 'None'}")
print(f"RAM: {result.ram}")
print(f"RAM Method: {result.ram_method}")
print(f"SSD: {result.ssd}")
print(f"Motherboard: {result.motherboard}")

# Check if 'hyperx' or 'fury' in normalized
print(f"\n'hyperx' in normalized: {'hyperx' in normalized}")
print(f"'fury' in normalized: {'fury' in normalized}")
print(f"'kingston' in normalized: {'kingston' in normalized}")
print(f"'corsair' in normalized: {'corsair' in normalized}")
print(f"'vengeance' in normalized: {'vengeance' in normalized}")

# Check RAM extraction
ram_capacity = cm._extract_ram_capacity(text)
ram_ddr = cm._extract_ram_ddr_type(text)
ram_speed = cm._extract_ram_frequency(text)
print(f"\nExtracted RAM: {ram_capacity}GB {ram_ddr} {ram_speed}")
