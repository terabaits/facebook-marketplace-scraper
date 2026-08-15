"""Debug full monitor scoring for dpfex.html"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

from src.scraper.computer_scraper import ComputerScraper
from src.utils.config import AppConfig
from src.utils.text import normalize_text
import re

config = AppConfig.from_yaml()

# Get monitors from database  
scraper = ComputerScraper(config)
scraper.initialize()
monitor_matcher = scraper.matcher.monitor_matcher

# Test text
text = """Datori un orgtehnika/Datori/ Pārdod
Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb
Var dabūt nedaudz lētak ar RAM 1x 16Gb
Monitors HP 24 collas dāvana"""

full_text = text.lower()
normalized = normalize_text(full_text)
monitor_context = monitor_matcher._extract_monitor_context(full_text)

# Extract specs
extracted_size = monitor_matcher._extract_size_from_text(full_text)
extracted_resolution = monitor_matcher._extract_resolution_from_text(full_text)
extracted_refresh = monitor_matcher._extract_refresh_rate(full_text)
extracted_panel = monitor_matcher._extract_panel_type(full_text)
is_included, detection_method = monitor_matcher._detect_monitor_mentioned(full_text)

print("=== EXTRACTED SPECS ===")
print(f"Size: {extracted_size}")
print(f"Resolution: {extracted_resolution}")
print(f"Refresh: {extracted_refresh}")
print(f"Panel: {extracted_panel}")
print(f"Is included: {is_included}")

print("\n=== SCORING HP 24\" MONITORS ===")

# Score all HP 24" monitors
hp_monitors = [m for m in monitor_matcher.monitors if m.brand.lower() == 'hp' and m.size and str(m.size) == '24']

results = []
for mon in hp_monitors:
    score = 0.0
    matches = []
    
    # Brand match
    brand_clean = normalize_text(mon.brand)
    if brand_clean in monitor_context:
        score += 0.30
        matches.append("brand")
    
    # Model match
    model_clean = normalize_text(mon.model)
    escaped = re.escape(model_clean)
    model_full_match = re.search(r'(?i)\b' + escaped + r'\b', monitor_context)
    if model_full_match:
        score += 0.50
        matches.append("model_full")
    else:
        # Check partial matches
        model_parts = mon.model.split()
        for part in model_parts:
            part_clean = normalize_text(part)
            if len(part_clean) >= 3:
                escaped = re.escape(part_clean)
                pattern = r'(?i)\b' + escaped + r'\b'
                if re.search(pattern, monitor_context):
                    score += 0.20
                    matches.append("model_partial")
                    break
    
    # Size match
    if mon.size and extracted_size:
        mon_size = str(int(float(mon.size))) if '.' in mon.size else mon.size
        if mon_size == extracted_size:
            score += 0.15
            matches.append("size")
    
    results.append((mon, score, matches))

# Sort by score
results.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 10 scoring monitors:")
for mon, score, matches in results[:10]:
    print(f"  {mon.brand} {mon.model}: score={score:.2f}, matches={matches}")

print(f"\n=== THRESHOLD CHECK ===")
best = results[0] if results else None
if best:
    mon, score, matches = best
    print(f"Best: {mon.brand} {mon.model} with score {score:.2f}")
    print(f"Has brand: {'brand' in '+'.join(matches)}")
    print(f"Has model: {'model_full' in '+'.join(matches) or 'model_partial' in '+'.join(matches)}")
    print(f"Has monitor_context: {is_included}")
    print(f"Score >= 0.45: {score >= 0.45}")
