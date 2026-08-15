#!/usr/bin/env python3
"""Test lphjf listing with full computer matcher logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository, GPUReferenceRepository, SSDReferenceRepository
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# Full listing text (based on typical structure)
listing_text = """Pārdod datoru. MSI MAG B650 TOMAHAWK WIFI
AMD Ryzen 7 8700F
RAM 32GB DDR5
SSD Kingston NV2 2TB
PSU Cooler Master V1200
Videokarte: Powercolor red devil RX6800XT 16gb
Procesors: Ryzen 7 8700F
Pamat plate: MSI MAG B650 TOMAHAWK WIFI
Video: Powercolor red devil RX6800XT 16gb
Operatīvā atmiņa, Gb: 32
HDD apjoms, Gb: 2000"""

normalized = normalize_text(listing_text)
text_lower = normalized.lower()

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)
    gpus = GPUReferenceRepository.get_all(session)
    ssds = SSDReferenceRepository.get_all(session)
    
    # Check GPU acceptance logic
    print("="*60)
    print("GPU CHECK")
    print("="*60)
    
    # Check what computer_matcher would do
    no_gpu_keywords = ['video nav', 'nav video', 'no gpu', 'gpu nav', 
                       'bez videokartes', 'bez video', 'nav videokarte',
                       'bez gpu', 'nav gpu']
    has_no_gpu = any(kw in text_lower for kw in no_gpu_keywords)
    print(f"has_no_gpu: {has_no_gpu}")
    
    # Check integrated graphics only
    igpu_keywords = ['integrated', 'integrētā', 'onboard', 'apu', 'vega', 'radeon graphics']
    has_igpu_mention = any(kw in text_lower for kw in igpu_keywords)
    print(f"has_igpu_mention: {has_igpu_mention}")
    
    # Check GPU mentions
    gpu_keywords = ['videokarte', 'video', 'gpu', 'radeon', 'nvidia', 'geforce', 'rtx', 'rx ', 'gtx']
    has_gpu_mention = any(kw in text_lower for kw in gpu_keywords)
    print(f"has_gpu_mention: {has_gpu_mention}")
    
    print(f"\nnormalized text around gpu mentions:")
    for kw in ['videokarte', 'video', 'radeon', 'rx6800']:
        if kw in text_lower:
            pos = text_lower.find(kw)
            print(f"  '{kw}' found at position {pos}: ...{normalized[pos-20:pos+50]}...")
    
    # Check SSD acceptance logic
    print("\n" + "="*60)
    print("SSD CHECK")
    print("="*60)
    
    # Look for Kingston in text
    print(f"'kingston' in normalized: {'kingston' in normalized}")
    print(f"'nv2' in normalized: {'nv2' in normalized}")
    
    # Check SSD keywords
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'm2', 'kingston', 'samsung', 'crucial', 'wd']
    has_ssd_mention = any(kw in text_lower for kw in ssd_keywords)
    print(f"has_ssd_mention: {has_ssd_mention}")
