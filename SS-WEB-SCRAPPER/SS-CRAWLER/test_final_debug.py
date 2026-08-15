# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSUReferenceRepository, CaseReferenceRepository,
    MotherboardReferenceRepository, MonitorReferenceRepository
)
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)

db = get_db_manager()

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

# Full test
title = "Datori un orgtehnika/Datori/ Pārdod"
desc = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500

Dators vel ar garantiju līdz šā gada beigām (PC veikals).

Dators atrodas Siguldā (Rīgā pievest var)."""

full_text = f"{title} {desc}".strip()
normalized = normalize_text(full_text)

print(f"Testing full computer matching...")
print(f"Full text (truncated): {full_text[:100]}...")
print(f"Normalized (truncated): {normalized[:100]}...")

# Check SSD extraction
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"\nSSD Capacity: {ssd_capacity}")

ssd_match = cm.ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
print(f"SSD Match: {ssd_match.ssd}")

if ssd_match.ssd:
    print(f"  Brand: {ssd_match.ssd.brand}")
    print(f"  Model: {ssd_match.ssd.model}")
    print(f"  Method: {ssd_match.method}")
    
    # Check brand in context
    ssd_brand_lower = ssd_match.ssd.brand.lower()
    print(f"\nLooking for '{ssd_brand_lower}' near SSD keywords...")
    
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'disk', 'cietie']
    for kw in ssd_keywords:
        if kw in normalized:
            kw_pos = normalized.find(kw)
            context_start = max(0, kw_pos - 40)
            context_end = min(len(normalized), kw_pos + 40)
            context = normalized[context_start:context_end]
            print(f"  Keyword '{kw}' at pos {kw_pos}")
            print(f"    Context: '{context[:60]}...'")
            if ssd_brand_lower in context:
                print(f"    -> BRAND FOUND!")
            else:
                print(f"    -> brand not in context")

# Run full match
result = cm.match(title, desc, 180.0)

print(f"\n\nFinal SSD result: {result.ssd}")
if result.ssd:
    print(f"  SSD: {result.ssd.get('brand')} {result.ssd.get('model')}")
    print(f"  ID: {result.ssd.get('id')}")
    print(f"  Method: {result.ssd_method}")
