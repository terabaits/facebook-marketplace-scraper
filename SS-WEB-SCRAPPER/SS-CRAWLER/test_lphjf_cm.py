#!/usr/bin/env python3
"""Test lphjf with actual computer matcher flow."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository, SSDReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# Full listing text
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

full_text = listing_text
text_lower = full_text.lower()
normalized = normalize_text(full_text)

config = AppConfig()
init_database(config.database)
db = get_db_manager()

def _extract_vram_mention(text):
    """Extract GPU VRAM mention from text."""
    import re
    text_lower = text.lower()
    
    # Look for VRAM patterns
    vram_patterns = [
        r'(\d+)\s*GB\s*(?:VRAM|Video|GPU|Graphics|Memory)',
        r'(?:VRAM|Video|GPU|Graphics|Memory)\s*(\d+)\s*GB',
        r'(\d+)\s*GB\s*(?:GDDR|Video)',
    ]
    for pattern in vram_patterns:
        match = re.search(pattern, text_lower)
        if match:
            gb = int(match.group(1))
            if 1 <= gb <= 64:
                return gb * 1024
    
    # Look for GPU VRAM in GPU context
    gpu_vram_pattern = r'(?:radeon|rtx|gtx|gpu).*?(\d+)\s*gb'
    match = re.search(gpu_vram_pattern, text_lower)
    if match:
        gb = int(match.group(1))
        if 1 <= gb <= 64:
            return gb * 1024
    
    return None

def _extract_ssd_capacity(text):
    """Extract SSD capacity from text."""
    import re
    text_lower = text.lower()
    
    # Look for TB patterns
    tb_match = re.search(r'(\d+(?:\.\d+)?)\s*TB', text, re.IGNORECASE)
    if tb_match:
        return int(float(tb_match.group(1)) * 1000)
    
    # Look for GB patterns
    gb_match = re.search(r'(\d{3,4})\s*GB', text, re.IGNORECASE)
    if gb_match:
        return int(gb_match.group(1))
    
    return None

with db.get_session() as session:
    print("="*60)
    print("LPHJF COMPUTER MATCHER SIMULATION")
    print("="*60)
    
    # Check GPU
    print("\n--- GPU CHECK ---")
    gpus = GPUReferenceRepository.get_all(session)
    gpu_matcher = GPUMatcher(gpus)
    
    vram_mb = _extract_vram_mention(full_text)
    print(f"Extracted VRAM: {vram_mb} MB ({vram_mb/1024 if vram_mb else 'N/A'} GB)")
    
    # Check for "no GPU" phrases
    has_no_gpu = any(kw in text_lower for kw in ['video nav', 'nav video', 'no gpu', 'gpu nav', 
                                                  'bez videokartes', 'bez video', 'nav videokarte',
                                                  'bez gpu', 'nav gpu'])
    print(f"has_no_gpu: {has_no_gpu}")
    
    # Match GPU
    gpu_match = gpu_matcher.match(full_text, "", vram_mb=vram_mb)
    print(f"Matched GPU: {gpu_match.gpu.name if gpu_match.gpu else 'None'}")
    print(f"Confidence: {gpu_match.confidence}")
    print(f"Method: {gpu_match.method}")
    
    if gpu_match.gpu and gpu_match.confidence >= 0.60:
        print("GPU WOULD BE ACCEPTED")
    else:
        print("GPU WOULD BE REJECTED")
    
    # Check SSD
    print("\n--- SSD CHECK ---")
    ssds = SSDReferenceRepository.get_all(session)
    ssd_matcher = SSDMatcher(ssds)
    
    ssd_capacity = _extract_ssd_capacity(full_text)
    print(f"Extracted SSD capacity: {ssd_capacity} GB")
    
    ssd_match = ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
    print(f"Matched SSD: {ssd_match.ssd.model if ssd_match.ssd else 'None'} (ID: {ssd_match.ssd.id if ssd_match.ssd else 'N/A'})")
    print(f"Brand: {ssd_match.ssd.brand if ssd_match.ssd else 'N/A'}")
    print(f"Method: {ssd_match.method}")
    print(f"Confidence: {ssd_match.confidence}")
