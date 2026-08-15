import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_session
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text

# Load SSDs
with get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)

# Initialize matcher
matcher = SSDMatcher(ssds)

# Test text
text = "Pārdodu jaudīgu un svaigu gaming pc. Visas detaļas, izņemot videokarti ir 3 mēnešus vecas.\n\nSpecifikācijas:\n\nRTX 3070 PNY\n\nI5-12400F\n\n16gb ram ddr4 3200mhz\n\n256GB nvme ssd\n\n700w psu"

normalized = normalize_text(text)
text_lower = normalized.lower()

print(f"Text: {text_lower}\n")

# Simulate SSD fallback logic
ssd_capacity = 256
best_match = None
best_score = 0

ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata', 'sandisk', 'seagate']

for ssd in matcher.ssds:
    if ssd.capacity_gb:
        tolerance = min(max(ssd_capacity * 0.1, 20), 100)
        if abs(ssd.capacity_gb - ssd_capacity) > tolerance:
            continue
    else:
        continue
    
    ssd_brand = ssd.brand.lower() if ssd.brand else ""
    model_lower = ssd.model.lower() if ssd.model else ""
    
    # This handles cases where all text is on one line
    ssd_context = text_lower
    
    # Find SSD brand mentions that appear near SSD keywords
    for brand in ssd_brand_keywords:
        if brand in text_lower:
            brand_pos = text_lower.find(brand)
            segment = text_lower[brand_pos:brand_pos + 80]
            if any(kw in segment for kw in ['ssd', 'nvme', 'm.2', 'hdd']):
                ssd_context = segment
                break
    
    # Check if brand appears in SSD context
    brand_in_text = ssd_brand in ssd_context
    
    # STRicter requirement: brand MUST be explicitly mentioned
    if not brand_in_text:
        continue
    
    # Check for specific model mentions
    model_in_text = False
    model_score = 0
    
    # Skip generic model names
    generic_models = {'ssd', 'hdd', 'nvme', 'disk', 'storage', 'eon', 'x3', 'extreme', 'aorus'}
    model_parts_for_generic = __import__('re').split(r'[/\s\-]+', model_lower)
    if any(part in generic_models for part in model_parts_for_generic):
        continue
    
    # Check for full model match
    if model_lower in ssd_context:
        model_in_text = True
        model_score = 20
    
    if brand_in_text or model_in_text:
        score = 0
        if brand_in_text:
            score += 5
        if model_in_text:
            score += model_score
        
        if (brand_in_text and model_in_text and score >= 15) or (brand_in_text and not model_in_text and score >= 5):
            if best_match is None or score > best_score:
                best_match = ssd
                best_score = score
                print(f"Found match: {ssd.brand} {ssd.model} (ID {ssd.id}) - score {score}")

if best_match:
    print(f"\nBest match: {best_match.brand} {best_match.model} (ID {best_match.id})")
else:
    print("\nNo match found - should fall back to generic")
