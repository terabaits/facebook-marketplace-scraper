# -*- coding: utf-8 -*-
"""Test all three listings with expected results."""
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

listings = [
    ("pbdhn", """Pārdod spēļu datoru
Cena 365 EUR
Procesors: AMD Ryzen 5 1600 6C/12T 3.2/3.6Ghz ar dzesētāju
Mātesplate: Gigabyte B450 Aorus Elite
Operatīvā atmiņa: DDR4 Patriot Viper Steel 2x4GB (8GB) 3200Mhz CL16-18-18-36
Cietie diski: SSD Crucial BX500 480GB + HDD WD Blue 1TB 7200RPM
Video karte: GTX 1060 6GB
Barošanas bloks: Cooler Master Elite V3 500W 80 Plus
Korpuss: Deepcool Matrexx 55 V3 ADD-RGB 3F (Melns)
Monitors: LG 24" 144hz 1ms IPS FullHD HDMI/DP/Audio""", 365.0,
     "RAM: ID 783 (Patriot Viper Steel 8GB), Monitor: ID 29860 (LG 24GN600-B)"),

    ("eiklm", """Pārdod spēļu datoru.
Procesors: Ryzen 7 5800X3D
Mātesplate: Gigabyte B450 Aorus Elite
Operatīvā atmiņa: DDR4 Kingston FURY Renegade 32GB 3600MHz
Cietie diski: SSD Kingston Renegade G5 1TB + HDD Seagate Barracuda 2TB
Video karte: Bez videokartes
Barošanas bloks: Corsair CS850M 850W
Korpuss: Deepcool
Dators ir pilnībā darba kārtībā, Windows 11 instalēts.
Cena 700 EUR.
Rīga""", 700.0,
     "GPU: None (bez videokartes)"),

    ("fpokc", """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini
Dators ir pilnībā darba kārtībā.
Cena 500 EUR.
Rīga""", 500.0,
     "SSD: ID 453 (Crucial MX500 1TB)"),
]

for listing_id, desc, price, expected in listings:
    print(f"\n{'='*70}")
    print(f"Listing: {listing_id}")
    print(f"Expected: {expected}")
    print('='*70)
    
    result = cm.match("Test", desc, price)
    
    print(f"\nActual Results:")
    if result.cpu:
        print(f"  CPU: {result.cpu.get('cpu_name')} (ID: {result.cpu.get('id')}) - {result.cpu_confidence:.0%}")
    if result.gpu:
        print(f"  GPU: {result.gpu.get('model')} (ID: {result.gpu.get('id')}) - {result.gpu_confidence:.0%}")
    else:
        print(f"  GPU: None")
    if result.ram:
        print(f"  RAM: {result.ram.get('name')} (ID: {result.ram.get('id')}) - {result.ram_confidence:.0%}")
    if result.ssd:
        print(f"  SSD: {result.ssd.get('name')} (ID: {result.ssd.get('id')}) - {result.ssd_confidence:.0%}")
    if result.monitor:
        print(f"  Monitor: {result.monitor.get('brand')} {result.monitor.get('model')} (ID: {result.monitor.get('id')}) - {result.monitor_confidence:.0%}")
    else:
        print(f"  Monitor: None")
