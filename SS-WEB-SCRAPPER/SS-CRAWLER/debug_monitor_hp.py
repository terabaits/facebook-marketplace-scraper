import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    monitors = MonitorRepository.get_all(session)

# Test text from listing
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

 E5-2680 v4"""

normalized = normalize_text(text)
print(f"Normalized text:\n{normalized}\n")

# Check if HP is in text
print(f"'hp' in text: {'hp' in normalized}")
print(f"'24' in text: {'24' in normalized}")

# Find HP monitors
print("\nHP monitors with '24' in model:")
for mon in monitors:
    if mon.brand and 'hp' in mon.brand.lower():
        if mon.model and '24' in mon.model:
            norm_name = normalize_text(f"{mon.brand} {mon.model}")
            print(f"  ID {mon.id}: {mon.brand} {mon.model}")
            print(f"    Size: {mon.size}", end="")
            if mon.size:
                print(f" ({type(mon.size).__name__})")
            else:
                print()
            print(f"    Normalized: '{norm_name}'")
            # Check if in text
            if 'hp' in normalized and str(mon.size) in normalized:
                print(f"    -> Size {mon.size} found in text")
