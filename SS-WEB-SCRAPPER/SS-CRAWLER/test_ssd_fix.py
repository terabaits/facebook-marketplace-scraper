#!/usr/bin/env python3
"""Test the SSD capacity extraction fix."""

import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.computer_matcher import ComputerMatcher
from src.models.schemas import SSDReference

# Connect to database
engine = create_engine('postgresql+psycopg2://crawler:crawler_pass@localhost:5433/ss_market')
Session = sessionmaker(bind=engine)
session = Session()

# Get SSD data from database
result = session.execute(text("SELECT * FROM ssd_reference"))

ssds = []
for row in result:
    row_dict = dict(row._mapping)
    ssd = SSDReference(
        id=row_dict.get('id'),
        brand=row_dict.get('brand', ''),
        model=row_dict.get('model', ''),
        capacity_gb=row_dict.get('capacity_gb'),
        interface=row_dict.get('interface'),
        form_factor=row_dict.get('form_factor'),
        controller=row_dict.get('controller'),
        configuration=row_dict.get('configuration'),
        has_dram=row_dict.get('has_dram'),
        hmb=row_dict.get('hmb'),
        nand_brand=row_dict.get('nand_brand'),
        nand_type=row_dict.get('nand_type'),
        layers=row_dict.get('layers'),
        read_speed_mb=row_dict.get('read_speed_mb'),
        write_speed_mb=row_dict.get('write_speed_mb'),
        category=row_dict.get('category'),
        notes=row_dict.get('notes'),
        search_keywords=row_dict.get('search_keywords', []),
        normalized_name=row_dict.get('normalized_name', f"{row_dict.get('brand', '')} {row_dict.get('model', '')}").strip()
    )
    ssds.append(ssd)

print(f"Loaded {len(ssds)} SSDs from database")

# Initialize computer matcher (need other components too)
from src.database.repository import ListingRepository

# Get CPUs
cpus = []
from src.models.schemas import CPUReference
result = session.execute(text("SELECT * FROM cpu_reference"))
for row in result:
    row_dict = dict(row._mapping)
    cpu = CPUReference(**row_dict)
    cpus.append(cpu)

# Get GPUs
gpus = []
from src.models.schemas import GPUReference
result = session.execute(text("SELECT * FROM gpu_reference"))
for row in result:
    row_dict = dict(row._mapping)
    gpu = GPUReference(**row_dict)
    gpus.append(gpu)

# Get RAMs
rams = []
from src.models.schemas import RAMReference
result = session.execute(text("SELECT * FROM ram_reference"))
for row in result:
    row_dict = dict(row._mapping)
    ram = RAMReference(**row_dict)
    rams.append(ram)

# Get PSUs
psus = []
from src.models.schemas import PSUReference
result = session.execute(text("SELECT * FROM psu_reference"))
for row in result:
    row_dict = dict(row._mapping)
    psu = PSUReference(**row_dict)
    psus.append(psu)

# Get Cases
cases = []
from src.models.schemas import CaseReference
result = session.execute(text("SELECT * FROM case_reference"))
for row in result:
    row_dict = dict(row._mapping)
    case = CaseReference(**row_dict)
    cases.append(case)

# Create computer matcher
matcher = ComputerMatcher(
    cpus=cpus,
    gpus=gpus,
    rams=rams,
    ssds=ssds,
    psus=psus,
    cases=cases
)

# Test the fcddo listing text
test_title = "Datori un orgtehnika/Datori/ Pārdod"
test_desc = """I5 4460, Gtx 1060, 16Gb Ram Gaming PC

Pārdodu jaudīgu spēļu datoru, kas lieliski piemērots videospēlēm, darbam, mācībām un citiem ikdienas uzdevumiem. 
Dators ir pilnībā darba kārtībā, apkalpots un gatavs lietošanai uzreiz pēc iegādes. 
Pavilks CS2, Fortnite, Valorant, GTA V, Minecraft, Roblox un daudzas citas spēles. 
Iespējama pārbaude iegādes brīdī. Atrodas Rīgā, Imantā. 

Продаю мощный игровой компьютер, который отлично подойдет для видеоигр, работы, учёбы и прочих повседневных задач. 
Компьютер полностью исправен, обслужен и готов к использованию сразу после покупки. 
Потянет CS2, Fortnite, Valorant, GTA V, Minecraft, Roblox и многие другие игры. 
Возможна проверка при покупке. Находится в Риге, в Иманте. 

Specifikācijas / Характеристики:
CPU: Intel Core i5 4460
GPU: NVIDIA GeForce GTX 1060 3GB
RAM: 16GB DDR3 Dual Channel
SSD: Crucial 120GB
HDD: WD Black 500GB
MBO: MSI H81M P33
PSU: FSP 500W"""

print("\n" + "="*80)
print("Testing fcddo listing...")
print("="*80)

result = matcher.match(test_title, test_desc, price=170.0)

print("\nMatched SSD:")
if result.ssd:
    print(f"  Brand: {result.ssd.get('brand', 'N/A')}")
    print(f"  Model: {result.ssd.get('model', 'N/A')}")
    print(f"  Capacity: {result.ssd.get('capacity_gb', 'N/A')}GB")
    print(f"  Confidence: {result.ssd_confidence:.1%}")
    print(f"  Method: {result.ssd_method}")
else:
    print("  No SSD matched!")
