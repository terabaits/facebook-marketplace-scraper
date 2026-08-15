# -*- coding: utf-8 -*-
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

# Test all three listings
listings = [
    ("aacph", "Datori un orgtehnika/Datori/ Pārdod", """Itel Core i5-9400f Coffee Lake 2.90 Ghz
Мат. пл. Gigabyte H310M S2H 2.0
G. Skill Ddr4-2666 32gb
Gigabyte Nvidia GeForce GTX 1660 6gb DDR5
SDD 512gb HDD 500gb
Windows 10
Monitor: AOC 25" LCD 2590G4""", 550.0),

    ("dpfex", "Datori un orgtehnika/Datori/ Pārdod", """Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb
Monitors HP 24 collas dāvana""", 230.0),

    ("acgdx", "Datori un orgtehnika/Datori/ Pārdod", """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)
Процессор: Intel Core i5-11400F
Видеокарта: Nvidia GeForce GTX 1650 (4GB)
Оперативная память: 16GB DDR4 3200 MHz
SSD: 1TB Kingston NV1
HDD: 2TB Seagate""", 300.0),
]

for listing_id, title, desc, price in listings:
    print(f"\n{'='*70}")
    print(f"Listing: {listing_id}")
    print('='*70)
    
    result = cm.match(title, desc, price)
    
    print(f"\nResults:")
    print(f"  CPU: {result.cpu.get('cpu_name') if result.cpu else 'None'} (ID: {result.cpu.get('id') if result.cpu else 'N/A'}) - {result.cpu_confidence:.0%}")
    print(f"  GPU: {result.gpu.get('model') if result.gpu else 'None'} - {result.gpu_confidence:.0%}")
    print(f"  RAM: {result.ram.get('name') if result.ram else 'None'} - {result.ram_confidence:.0%}")
    print(f"  SSD: {result.ssd.get('name') if result.ssd else 'None'} - {result.ssd_confidence:.0%}")
    if result.additional_ssds:
        for i, ssd in enumerate(result.additional_ssds, 2):
            print(f"    SSD {i}: {ssd['brand']} {ssd['capacity_gb']}GB")
    print(f"  Motherboard: {result.motherboard.get('model') if result.motherboard else 'None'} (ID: {result.motherboard.get('id') if result.motherboard else 'N/A'}) - {result.motherboard_confidence:.0%}")
    print(f"  Monitor: {result.monitor.get('model') if result.monitor else 'None'} - {result.monitor_confidence:.0%}")
