# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

# Force reload of modules
import importlib
import src.scraper.ssd_matcher
importlib.reload(src.scraper.ssd_matcher)

import src.scraper.computer_matcher
importlib.reload(src.scraper.computer_matcher)

import re
from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

matcher = SSDMatcher(ssds)

# Test the actual match_listing with 256 capacity
text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

print("Direct SSDMatcher test...")
result = matcher.match_listing(text, extracted_capacity=256)
print(f"Result: {result.ssd}")
if result.ssd:
    print(f"  Brand: {result.ssd.brand}")
    print(f"  Model: {result.ssd.model}")
    print(f"  ID: {result.ssd.id}")

# Now test computer_matcher
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    PSUReferenceRepository, CaseReferenceRepository, MotherboardReferenceRepository,
    MonitorReferenceRepository
)

with db.get_session() as session:
    cm = ComputerMatcher(
        cpus=CPUReferenceRepository.get_all(session),
        gpus=GPUReferenceRepository.get_all(session),
        rams=RAMReferenceRepository.get_all(session),
        ssds=SSDReferenceRepository.get_all(session),
        psus=PSUReferenceRepository.get_all(session),
        cases=CaseReferenceRepository.get_all(session),
        motherboards=MotherboardReferenceRepository.get_all(session),
        monitors=MonitorReferenceRepository.get_all(session)
    )

print("\n\nComputerMatcher test...")
result = cm.match("pcneb", text, text, 180.0)
print(f"SSD: {result.ssd}")
if result.ssd:
    print(f"  SSD ID: {result.ssd.get('id')}")
    print(f"  Brand: {result.ssd.get('brand')}")
    print(f"  Model: {result.ssd.get('model')}")
