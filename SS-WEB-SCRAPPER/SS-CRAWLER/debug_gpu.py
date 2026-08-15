# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

# Clear any cached modules
import importlib
import src.scraper.computer_matcher
importlib.reload(src.scraper.computer_matcher)

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    # Initialize ComputerMatcher like the scraper does
    matcher = ComputerMatcher(session)

# Test full text from lphjf.html
text = """Ryzen 7 8700f, Rx6800Xt 16gb, 2tb ssd, 32gb ddr5, jaudīgs dators - perfekts jaunākajām datorspēlēm un ikdienai. Iespējams iegādāties bez videokartes.

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

normalized = normalize_text(text)
print("Checking GPU matching...")
print(f"_has_integrated_graphics_only: {matcher._has_integrated_graphics_only(normalized)}")

# Check for "no GPU" indicators
text_lower = text.lower()
no_gpu = any(kw in text_lower for kw in ['video nav', 'nav video', 'bez video', 'no gpu', 'bez gpu', 'gpu nav'])
print(f"has_no_gpu: {no_gpu}")

# Check VRAM extraction
vram = matcher._extract_vram_mention(text)
print(f"VRAM extracted: {vram}")

# Now try matching
if not matcher._has_integrated_graphics_only(normalized) and not no_gpu:
    print("\nAttempting GPU match...")
    gpu_match = matcher.gpu_matcher.match(text, "", vram_mb=vram)
    print(f"GPU match result: {gpu_match}")
    print(f"Confidence: {gpu_match.confidence}")
    print(f"GPU: {gpu_match.gpu}")
else:
    print("\nGPU matching skipped!")
