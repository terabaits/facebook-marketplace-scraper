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
from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
from src.utils.config import AppConfig
from src.utils.text import normalize_text

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)
    gpus = GPUReferenceRepository.get_all(session)
    rams = RAMReferenceRepository.get_all(session)
    ssds = SSDReferenceRepository.get_all(session)
    psus = PSURepository.get_all(session)
    cases = CaseRepository.get_all(session)
    mbs = MotherboardRepository.get_all(session)
    monitors = MonitorRepository.get_all(session)

# Initialize matcher
matcher = ComputerMatcher(cpus, gpus, rams, ssds, psus, cases, mbs, monitors)

# Test with actual listing text
text = """Pārdodu PC

Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng

 Procesors:

 E5-2680 v4

 Procesora frekvence, Ghz:

 3300

 Pamat plate:

 Qiyda x99

 Video:

 Rx 580 8gb

 Operatīvā atmiņa, Gb:

 32

 HDD apjoms, Gb:

 628

 DVD:

 CD-RW

 Stāvoklis:

 lietota

 Cena:

 230"""

print("Calling ComputerMatcher.match_listing...")
result = matcher.match_listing(text)
print("\nResults:")
print(f"  CPU: {result.cpu}")
print(f"  GPU: {result.gpu}")
print(f"  RAM: {result.ram}")
print(f"  SSD: {result.ssd}")
print(f"  Motherboard: {result.motherboard}")
print(f"  Monitor: {result.monitor}")
