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
        psus=PSURepository.get_all(session),
        cases=CaseRepository.get_all(session),
        motherboards=MotherboardRepository.get_all(session),
        monitors=MonitorRepository.get_all(session)
    )

# Full acgdx text
desc = """Игровой ПК (i5-11400F / Gtx 1650 / 16Gb / Ssd 1Tb + Hdd 2Tb)
Полностью рабочий компьютер, подходит для игр и повседневных задач.
Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)
Видеокарта: Nvidia GeForce GTX 1650 (4GB)
Оперативная память: 16GB DDR4 3200 MHz
SSD: 1TB Kingston NV1
HDD: 2TB Seagate
Блок питания: 650W"""

full_text = desc
normalized = normalize_text(full_text)

print(f"Testing acgdx SSD matching in computer_matcher...")
print(f"Full text (truncated): {full_text[:100]}...")
print(f"Normalized (truncated): {normalized[:100]}...")

# Check SSD extraction
ssd_capacity = cm._extract_ssd_capacity(full_text)
print(f"\nSSD Capacity extracted: {ssd_capacity}")

ssd_match = cm.ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
print(f"ssd_match.ssd: {ssd_match.ssd}")

if ssd_match.ssd:
    print(f"\nSSD found: {ssd_match.ssd.brand} {ssd_match.ssd.model}")
    print(f"  Method: {ssd_match.method}")
    
    ssd_brand = normalize_text(ssd_match.ssd.brand)
    ssd_model = normalize_text(ssd_match.ssd.model)
    has_brand = ssd_brand in normalized
    
    print(f"\n  ssd_brand: '{ssd_brand}'")
    print(f"  has_brand (in normalized): {has_brand}")
    
    # Check SSD context
    ssd_brand_in_ssd_context = False
    ssd_brand_lower = ssd_match.ssd.brand.lower()
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'disk', 'cietie']
    print(f"\n  Looking for '{ssd_brand_lower}' near SSD keywords...")
    for kw in ssd_keywords:
        if kw in normalized:
            kw_pos = normalized.find(kw)
            context_start = max(0, kw_pos - 40)
            context_end = min(len(normalized), kw_pos + 40)
            context = normalized[context_start:context_end]
            print(f"    Keyword '{kw}' at pos {kw_pos}")
            if ssd_brand_lower in context:
                ssd_brand_in_ssd_context = True
                print(f"      -> BRAND FOUND in context!")
            else:
                print(f"      -> brand not in context: '{context[:50]}'")
    
    # Check model in text
    has_model_in_text = ssd_model in normalized
    print(f"\n  ssd_model: '{ssd_model}'")
    print(f"  has_model_in_text: {has_model_in_text}")
    
    is_exact = ssd_match.method.split('+')[0] == 'exact'
    is_model_part = 'model_part' in ssd_match.method
    is_capacity_match = 'capacity_exact' in ssd_match.method or 'capacity_near' in ssd_match.method
    
    print(f"\n  is_exact: {is_exact}")
    print(f"  is_model_part: {is_model_part}")
    print(f"  is_capacity_match: {is_capacity_match}")
    print(f"  ssd_brand_in_ssd_context: {ssd_brand_in_ssd_context}")
    
    is_specific_ssd = is_exact or (is_model_part and has_model_in_text and has_brand) or (is_capacity_match and ssd_brand_in_ssd_context)
    print(f"\n  is_specific_ssd: {is_specific_ssd}")
