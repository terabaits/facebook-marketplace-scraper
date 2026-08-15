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

# Test aacph
title = "Datori un orgtehnika/Datori/ Pārdod"
desc = """Itel Core i5-9400f Coffee Lake 2.90 Ghz
Мат. пл. Gigabyte H310M S2H 2.0
G. Skill Ddr4-2666 32gb
Gigabyte Nvidia GeForce GTX 1660 6gb DDR5
SDD 512gb HDD 500gb
Windows 10
Monitor: AOC 25" LCD 2590G4
Riga, Jelgava, Dobele."""

print("Testing aacph full matching...")
result = cm.match(title, desc, 550.0)

print(f"\nResults:")
print(f"  CPU: {result.cpu.get('cpu_name') if result.cpu else 'None'} (ID: {result.cpu.get('id') if result.cpu else 'N/A'})")
print(f"  GPU: {result.gpu.get('model') if result.gpu else 'None'}")
print(f"  RAM: {result.ram}")
print(f"  SSD: {result.ssd}")
print(f"  Motherboard: {result.motherboard}")
print(f"  Monitor: {result.monitor}")
