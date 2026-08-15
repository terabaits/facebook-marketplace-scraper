# -*- coding: utf-8 -*-
"""Debug three new listings."""
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

# Listing 1: alnnx - RAM should be ID 3289 (Kingston HyperX), Motherboard ID 7446 (Asus TUF)
desc_alnnx = """Pārdod spēļu datoru.
Procesors: AMD Ryzen 5 1600X 3.6GHz
Mātesplate: Asus TUF B450-PLUS GAMING
Operatīvā atmiņa: HyperX Fury DDR4 16GB 3200MHz
Video karte: GTX 1060 3GB"""

# Listing 2: fcddo - CPU should be i5-4460 (not i5-4460S)
desc_fcddo = """Pārdod datoru.
Procesors: Intel Core i5-4460
Mātesplate: MSI H81M Eco
Operatīvā atmiņa: DDR3 16GB
Video karte: GTX 1060 3GB"""

# Listing 3: kbdee - SSD should be ID 817 (Kingston A2000)
desc_kbdee = """Pārdod jaunu spēļu datoru.
Procesors: Intel Core i7-14700KF
Mātesplate: Asus PRIME Z790-P
Operatīvā atmiņa: Corsair Vengeance 32GB 6000MHz
Cietie diski: SSD Kingston A2000 1TB NVMe
Video karte: RTX 5070 12GB
Barošanas bloks: Corsair RM1000 1000W"""

listings = [
    ("alnnx", desc_alnnx, 230.0, "RAM ID 3289 (Kingston HyperX), MB ID 7446 (Asus TUF)"),
    ("fcddo", desc_fcddo, 170.0, "CPU i5-4460 (not i5-4460S)"),
    ("kbdee", desc_kbdee, 1499.0, "SSD ID 817 (Kingston A2000)"),
]

for listing_id, desc, price, expected in listings:
    print(f"\n{'='*70}")
    print(f"Listing: {listing_id}")
    print(f"Expected: {expected}")
    print('='*70)
    
    normalized = normalize_text(desc)
    print(f"Normalized: {normalized[:120]}...\n")
    
    result = cm.match("Test", desc, price)
    
    if listing_id == "alnnx":
        print(f"RAM: {result.ram}")
        print(f"RAM Method: {result.ram_method}")
        print(f"\nMotherboard: {result.motherboard}")
        print(f"MB Method: {result.motherboard_method}")
        
        # Check if hyperx/fury in normalized
        print(f"\n'hyperx' in normalized: {'hyperx' in normalized}")
        print(f"'fury' in normalized: {'fury' in normalized}")
        print(f"'tuf' in normalized: {'tuf' in normalized}")
        
    elif listing_id == "fcddo":
        print(f"CPU: {result.cpu}")
        print(f"CPU Method: {result.cpu_method}")
        print(f"\n'i54460' in normalized: {'i54460' in normalized}")
        
    elif listing_id == "kbdee":
        print(f"SSD: {result.ssd}")
        print(f"SSD Method: {result.ssd_method}")
        print(f"\n'kingston' in normalized: {'kingston' in normalized}")
        print(f"'a2000' in normalized: {'a2000' in normalized}")
        print(f"'nvme' in normalized: {'nvme' in normalized}")
