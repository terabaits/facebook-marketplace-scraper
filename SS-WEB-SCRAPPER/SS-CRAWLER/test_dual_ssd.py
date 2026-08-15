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

# Test with dual SSD text
title = "Test PC"
desc = """PC specs:
- CPU: i5-10400
- 1x SSD 128gb NVMe
- 1x SSD 500gb SATA
- RAM: 16GB
"""

print("Testing dual SSD detection...")
result = cm.match(title, desc, 500.0)

print(f"\nPrimary SSD: {result.ssd}")
print(f"Additional SSDs: {result.additional_ssds}")

if result.additional_ssds:
    for i, ssd in enumerate(result.additional_ssds, 2):
        print(f"  SSD {i}: {ssd['brand']} {ssd['capacity_gb']}GB ({ssd['type']})")
