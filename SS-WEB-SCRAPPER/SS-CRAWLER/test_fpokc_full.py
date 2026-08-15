# -*- coding: utf-8 -*-
"""Test complete fpokc listing."""
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

# Full fpokc text
text = """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini
Dators ir pilnībā darba kārtībā.
Cena 500 EUR.
Rīga"""

print("Testing complete fpokc listing...")
result = cm.match("Test", text, 500.0)

print(f"\nResults:")
print(f"CPU: {result.cpu.get('cpu_name') if result.cpu else 'None'} (ID: {result.cpu.get('id') if result.cpu else 'N/A'})")
print(f"GPU: {result.gpu.get('model') if result.gpu else 'None'} (ID: {result.gpu.get('id') if result.gpu else 'N/A'})")
print(f"RAM: {result.ram.get('name') if result.ram else 'None'} (ID: {result.ram.get('id') if result.ram else 'N/A'})")
print(f"SSD: {result.ssd.get('name') if result.ssd else 'None'} (ID: {result.ssd.get('id') if result.ssd else 'N/A'})")
print(f"Method: {result.ssd_method}")
