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

# Listing 1: pbdhn - RAM should be ID 783 (Patriot Viper Steel 8 GB)
desc_pbdhn = """Pārdod spēļu datoru
Cena 365 EUR
Procesors: AMD Ryzen 5 1600 6C/12T 3.2/3.6Ghz ar dzesētāju
Mātesplate: Gigabyte B450 Aorus Elite
Operatīvā atmiņa: DDR4 Patriot Viper Steel 2x4GB (8GB) 3200Mhz CL16-18-18-36
Cietie diski: SSD Crucial BX500 480GB + HDD WD Blue 1TB 7200RPM
Video karte: GTX 1060 6GB
Barošanas bloks: Cooler Master Elite V3 500W 80 Plus
Korpuss: Deepcool Matrexx 55 V3 ADD-RGB 3F (Melns)
Monitors: LG 24" 144hz 1ms IPS FullHD HDMI/DP/Audio"""

# Listing 2: eiklm - No GPU ("bez videokartes")
desc_eiklm = """Pārdod spēļu datoru.
Procesors: Ryzen 7 5800X3D
Mātesplate: Gigabyte B450 Aorus Elite
Operatīvā atmiņa: DDR4 Kingston FURY Renegade 32GB 3600MHz
Cietie diski: SSD Kingston Renegade G5 1TB + HDD Seagate Barracuda 2TB
Video karte: Bez videokartes
Barošanas bloks: Corsair CS850M 850W
Korpuss: Deepcool
Dators ir pilnībā darba kārtībā, Windows 11 instalēts.
Cena 700 EUR.
Rīga"""

# Listing 3: fpokc - SSD should be ID 449 (Crucial), not 587
desc_fpokc = """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini
Dators ir pilnībā darba kārtībā.
Cena 500 EUR.
Rīga"""

listings = [
    ("pbdhn", desc_pbdhn, 365.0, "RAM ID 783 (Patriot Viper Steel 8GB), Monitor ID 29860 (LG 24GN600-B)"),
    ("eiklm", desc_eiklm, 700.0, "NO GPU (bez videokartes)"),
    ("fpokc", desc_fpokc, 500.0, "SSD ID 449 (Crucial MX500), not 587"),
]

for listing_id, desc, price, expected in listings:
    print(f"\n{'='*70}")
    print(f"Listing: {listing_id} - Expected: {expected}")
    print('='*70)
    
    normalized = normalize_text(desc)
    print(f"Normalized text (first 200 chars): {normalized[:200]}...")
    
    if listing_id == "pbdhn":
        # Check RAM
        print("\n--- RAM Check ---")
        ram_capacity = cm._extract_ram_capacity(desc)
        ram_ddr = cm._extract_ram_ddr_type(desc)
        print(f"RAM Capacity: {ram_capacity}, DDR: {ram_ddr}")
        print(f"'patriot' in normalized: {'patriot' in normalized}")
        print(f"'viper' in normalized: {'viper' in normalized}")
        print(f"'vipersteel' in normalized: {'vipersteel' in normalized}")
        
        # Check Monitor
        print("\n--- Monitor Check ---")
        print(f"'lg' in normalized: {'lg' in normalized}")
        print(f"'24' in normalized: {'24' in normalized}")
        print(f"'144hz' in normalized: {'144hz' in normalized}")
        print(f"'monitor' in normalized: {'monitor' in normalized}")
        
    elif listing_id == "eiklm":
        # Check GPU
        print("\n--- GPU Check ---")
        print(f"'bez' in normalized: {'bez' in normalized}")
        print(f"'videokartes' in normalized: {'videokartes' in normalized}")
        print(f"'bez videokartes' in normalized: {'bez videokartes' in normalized}")
        has_no_gpu = cm._has_no_gpu(desc)
        print(f"_has_no_gpu(): {has_no_gpu}")
        
    elif listing_id == "fpokc":
        # Check SSD
        print("\n--- SSD Check ---")
        ssd_capacity = cm._extract_ssd_capacity(desc)
        print(f"SSD Capacity extracted: {ssd_capacity}")
        print(f"'crucial' in normalized: {'crucial' in normalized}")
        print(f"'mx500' in normalized: {'mx500' in normalized}")
        
        ssd_match = cm.ssd_matcher.match_listing(desc, extracted_capacity=ssd_capacity)
        if ssd_match.ssd:
            print(f"SSD Match: ID {ssd_match.ssd.id} - {ssd_match.ssd.brand} {ssd_match.ssd.model}")
            print(f"  Method: {ssd_match.method}")
        else:
            print("No SSD match")
    
    # Run full match
    result = cm.match("Test", desc, price)
    print(f"\n--- FULL RESULT ---")
    if listing_id == "pbdhn":
        print(f"RAM: {result.ram}")
        print(f"Monitor: {result.monitor}")
    elif listing_id == "eiklm":
        print(f"GPU: {result.gpu} (should be None)")
    elif listing_id == "fpokc":
        print(f"SSD: {result.ssd}")
