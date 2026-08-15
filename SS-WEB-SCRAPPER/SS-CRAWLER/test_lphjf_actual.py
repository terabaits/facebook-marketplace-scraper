#!/usr/bin/env python3
"""Test with actual lphjf listing text."""
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository, SSDReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# ACTUAL listing text from lphjf
listing_text = """Ryzen 7 8700f, Rx6800Xt 16gb, 2tb ssd, 32gb ddr5, jaudīgs dators - perfekts jaunākajām datorspēlēm un ikdienai. Iespējams iegādāties bez videokartes.
- Datoram ir jauns korpuss, cpu, ūdensdzese, operatīvā atmiņa, ssd disks. Garantija mēnesis visam datoram.
- Ideāls datorspēlēm RX6800XT videokarti.
- Perfekti salikts, kluss un kvalitatīvs.
- Pie iegādes iespējams notestēt un pārliecināties par datora darbību. Atrodas centrā.
Komponentes/составные части:
Procesors: AMD Ryzen r7 8700f - jauns;
Mātesplate: MSI B650 Tomahawk WIFI - lietota;
Operatīvā atmiņa: ddr5 samsung 2x16 laptop ram ar adapteriem 5200mhz.
Cietie diski: Kinsgotn NV2 Pcie 4.0 2tb m. 2 ssd - jauns;
Videokarte: Powercolor red devil RX6800XT 16gb - lietota;
Barības bloks: CoolerMaster V1200 1200W 80+Platinum - lietots;
Korpuss: BeQuiet. 802 window - jauns;
Dzesētājs: Arctic 360mm LiquidFreezer iii - jauns;
Operētājsistēma: Microsoft Windows 11 Professional;"""

full_text = listing_text
text_lower = full_text.lower()
normalized = normalize_text(full_text)

print("="*60)
print("ACTUAL LPHJF TEXT ANALYSIS")
print("="*60)
print(f"\nNormalized text:\n{normalized}\n")

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    print("="*60)
    print("GPU CHECK")
    print("="*60)
    
    gpus = GPUReferenceRepository.get_all(session)
    gpu_matcher = GPUMatcher(gpus)
    
    # Check "no GPU" phrases
    no_gpu_keywords = ['video nav', 'nav video', 'no gpu', 'gpu nav', 
                       'bez videokartes', 'bez video', 'nav videokarte',
                       'bez gpu', 'nav gpu']
    has_no_gpu = any(kw in text_lower for kw in no_gpu_keywords)
    print(f"has_no_gpu (old check): {has_no_gpu}")
    
    # But the phrase "bez videokartes" can mean "can be purchased without video card"
    # If a GPU model is explicitly mentioned, we should NOT skip matching
    gpu_mentioned = any(kw in text_lower for kw in ['rx6800', 'rx 6800', 'videokarte:', 'video:'])
    print(f"GPU model mentioned: {gpu_mentioned}")
    
    if has_no_gpu and gpu_mentioned:
        print("GPU is mentioned despite 'bez videokartes' - should NOT skip")
        has_no_gpu = False
    
    # Check integrated graphics only
    igpu_keywords = ['integrated', 'integrētā', 'onboard', 'apu', 'vega', 'radeon graphics']
    has_igpu_mention = any(kw in text_lower for kw in igpu_keywords)
    print(f"has_igpu_mention: {has_igpu_mention}")
    
    # Check what _has_integrated_graphics_only would return
    igpu_only_patterns = [
        r'\bintegrēt[āa]\b', r'\bintegrated\b', r'\bonboard\b',
        r'\bapu\b', r'\bvega\s*\d*\b', r'\bradeon\s+graphics\b',
        r'\bnavi\s*\d*\b',
    ]
    has_igpu_only = False
    for pattern in igpu_only_patterns:
        if re.search(pattern, text_lower):
            has_igpu_only = True
            print(f"  Found iGPU pattern: {pattern}")
    print(f"has_igpu_only: {has_igpu_only}")
    
    # Now match GPU
    if not has_igpu_only and not has_no_gpu:
        gpu_match = gpu_matcher.match(full_text, "", vram_mb=None)
        print(f"\nMatched GPU: {gpu_match.gpu.name if gpu_match.gpu else 'None'}")
        print(f"Confidence: {gpu_match.confidence}")
        print(f"Method: {gpu_match.method}")
        
        if gpu_match.gpu and gpu_match.confidence >= 0.60:
            print("GPU WOULD BE ACCEPTED")
        else:
            print("GPU WOULD BE REJECTED")
    else:
        print("\nGPU matching SKIPPED due to has_igpu_only or has_no_gpu")
    
    print("\n" + "="*60)
    print("SSD CHECK")
    print("="*60)
    
    ssds = SSDReferenceRepository.get_all(session)
    ssd_matcher = SSDMatcher(ssds)
    
    # Check for Kingston in text
    print(f"'kingston' in normalized: {'kingston' in normalized}")
    print(f"'kinsgotn' in normalized: {'kinsgotn' in normalized}")
    print(f"'nv2' in normalized: {'nv2' in normalized}")
    
    # Try matching with typo
    ssd_match = ssd_matcher.match_listing(full_text, extracted_capacity=2000)
    print(f"\nMatched SSD: {ssd_match.ssd.model if ssd_match.ssd else 'None'} (ID: {ssd_match.ssd.id if ssd_match.ssd else 'N/A'})")
    print(f"Brand: {ssd_match.ssd.brand if ssd_match.ssd else 'N/A'}")
    print(f"Method: {ssd_match.method}")
    print(f"Confidence: {ssd_match.confidence}")
