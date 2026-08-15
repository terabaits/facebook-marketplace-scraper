# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository
from src.scraper.cpu_matcher import CPUMatcher
from src.utils.config import AppConfig
from src.utils.text import extract_cpu_tokens, normalize_text

config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)

matcher = CPUMatcher(cpus)

# Test text from pbdhn.html
text = """Sveiki, pārdodu labu, ātru un jaudīgu datoru. Dators izmantots 2 gadus - gan darbam, gan spēlēm. Nav ne reizi "crashojis". Strādāja ļoti labi un bez problēmām, mierīgi pavelk dažāda satura spēles.

Pārdodu, jo tik bieži vairs nesanāk būt mājās, kā arī nevēlos, lai krāj putekļus ;)

Komponentes:

 CPU - AMD R5 1600 3.2 GHz

 GPU - NVIDIA GeForce GTX 1060 6GB

 RAM - 2 x 4GB Viper Steel gaming DDR4 3200Mhz

 MB - B450 Aorus Elite

 PSU - 500W EcoSeries

 Storage - Crucial BX500 SAT 6gb/s 480GB SSD

 Cooling - 5 RF120M RGB Fans

Un komplektā nāk vēl:

 Monitors - UltraGear 24GN600 144Hz 1ms (ideālā stāvoklī bez švīkām vai darbības traucējumiem)

 Klaviatūra - Royal Kludge RK84 red switch

Par vairāk jautājumiem droši rakstat.

 Procesors:

 Amd r5 1600

 Procesora frekvence, Ghz:

 3.20"""

normalized = normalize_text(text)
print("Normalized text:")
print(normalized)
print()

print("Extracted CPU tokens:")
tokens = extract_cpu_tokens(text)
for token in tokens:
    print(f"  '{token}'")
print()

# Check if "r51600" is in the tokens
print("Looking for 'r51600' or similar...")
for token in tokens:
    if '1600' in token or 'r5' in token:
        print(f"  Found: '{token}'")

# Run the matcher
print("\nRunning CPU matcher...")
result = matcher.match("", text)
print(f"Result: {result}")
