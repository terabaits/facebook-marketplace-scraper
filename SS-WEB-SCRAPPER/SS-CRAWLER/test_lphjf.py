#!/usr/bin/env python3
"""Test lphjf listing issues."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository, SSDReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# Based on the listing text - Powercolor red devil RX6800XT 16gb
listing_text = """
Videokarte: Powercolor red devil RX6800XT 16gb
SSD: Kingston NV2 2TB
"""

normalized = normalize_text(listing_text)
print(f"Normalized text:\n{normalized}\n")

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("="*60)
    print("GPU TEST: Should match Radeon RX 6800 XT (ID 315)")
    print("Text: 'Powercolor red devil RX6800XT 16gb'")
    print("="*60)
    
    gpus = GPUReferenceRepository.get_all(session)
    gpu_matcher = GPUMatcher(gpus)
    
    # Check for RX 6800 XT in DB
    print("\nRX 6800 XT GPUs in DB:")
    for gpu in gpus:
        if '6800' in gpu.name.lower() or '6800xt' in gpu.name.lower():
            print(f"  ID {gpu.id}: {gpu.name}")
    
    # Try matching
    gpu_result = gpu_matcher.match(listing_text)
    print(f"\nMatched GPU: {gpu_result.gpu.name if gpu_result.gpu else 'None'} (ID: {gpu_result.gpu.id if gpu_result.gpu else 'N/A'})")
    print(f"Method: {gpu_result.method}")
    print(f"Confidence: {gpu_result.confidence}")
    
    print("\n" + "="*60)
    print("SSD TEST: Should match Kingston NV2 (ID 859)")
    print("Text: 'Kingston NV2 2TB'")
    print("="*60)
    
    ssds = SSDReferenceRepository.get_all(session)
    ssd_matcher = SSDMatcher(ssds)
    
    # Check for Kingston NV2 in DB
    print("\nKingston NV2 SSDs in DB:")
    for ssd in ssds:
        ssd_name = ssd.model if hasattr(ssd, 'model') else str(ssd)
        if 'nv2' in ssd_name.lower():
            print(f"  ID {ssd.id}: {ssd_name} - {ssd.capacity_gb}GB")
    
    # Try matching
    ssd_result = ssd_matcher.match_listing(listing_text, extracted_capacity=2000)
    print(f"\nMatched SSD: {ssd_result.ssd.model if ssd_result.ssd else 'None'} (ID: {ssd_result.ssd.id if ssd_result.ssd else 'N/A'})")
    print(f"Method: {ssd_result.method}")
    print(f"Confidence: {ssd_result.confidence}")
