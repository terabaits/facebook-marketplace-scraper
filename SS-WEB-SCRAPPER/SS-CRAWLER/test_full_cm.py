# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSUReferenceRepository, CaseReferenceRepository,
    MotherboardReferenceRepository, MonitorReferenceRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
from src.utils.logger import get_logger

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    matcher = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSUReferenceRepository.get_all(session),
        cases=CaseReferenceRepository.get_all(session),
        motherboards=MotherboardReferenceRepository.get_all(session),
        monitors=MonitorReferenceRepository.get_all(session)
    )

# Test text from pcneb.html
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

print("Testing computer_matcher.match()...")

result = matcher.match("pcneb", text, text, 180.0)

print(f"\nSSD Result: {result.ssd}")
print(f"SSD Confidence: {result.ssd_confidence}")
print(f"SSD Method: {result.ssd_method}")
