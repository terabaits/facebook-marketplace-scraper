import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_session
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text

# Load SSDs
with get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

print(f"Loaded {len(ssds)} SSDs")

# Initialize matcher
matcher = SSDMatcher(ssds)

# Check CS1030
ssd_1381 = matcher.id_to_ssd.get(1381)
if ssd_1381:
    print(f"\nSSD ID 1381: {ssd_1381.brand} {ssd_1381.model}")
    print(f"  Capacity: {ssd_1381.capacity_gb}")
    print(f"  Brand lower: '{ssd_1381.brand.lower()}'")

# Test text
text = "Pārdodu jaudīgu un svaigu gaming pc. Visas detaļas, izņemot videokarti ir 3 mēnešus vecas.\n\nSpecifikācijas:\n\nRTX 3070 PNY\n\nI5-12400F\n\n16gb ram ddr4 3200mhz\n\n256GB nvme ssd\n\n700w psu\n\nAtrodas Rīgā, Purvciemā. Var sarunāt piegādi."

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"\nNormalized text:\n{normalized}\n")
print(f"Text lower:\n{text_lower}\n")

# Check if 'teamgroup' is in the text
print(f"'teamgroup' in text_lower: {'teamgroup' in text_lower}")
print(f"'cs1030' in text_lower: {'cs1030' in text_lower}")

# Check ssd_context generation
ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata', 'sandisk', 'seagate']
for brand in ssd_brand_keywords:
    if brand in text_lower:
        brand_pos = text_lower.find(brand)
        segment = text_lower[brand_pos:brand_pos + 80]
        print(f"Found '{brand}' in text, segment: '{segment}'")
