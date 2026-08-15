"""Trace monitor matching step by step"""
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

# Extract specs
extracted_size = monitor_matcher._extract_size_from_text(full_text)
is_included, detection_method = monitor_matcher._detect_monitor_mentioned(full_text)
has_explicit_monitor = monitor_matcher._has_explicit_monitor_context(full_text)
monitor_context = monitor_matcher._extract_monitor_context(full_text)

print("=== SETUP ===")
print(f"extracted_size: {extracted_size}")
print(f"is_included: {is_included}")
print(f"has_explicit_monitor: {has_explicit_monitor}")
print(f"monitor_context: '{monitor_context}'")

print("\n=== SCORING ALL MONITORS ===")
best_match = None
best_score = 0.0
best_method = ""

for mon in monitor_matcher.monitors:
    score = 0.0
    matches = []
    
    # Brand match
    brand_clean = normalize_text(mon.brand)
    if brand_clean in monitor_context:
        score += 0.30
        matches.append("brand")
    
    # Model match (full)
    model_clean = normalize_text(mon.model)
    escaped = re.escape(model_clean)
    model_full_match = re.search(r'(?i)\b' + escaped + r'\b', monitor_context)
    if model_full_match:
        score += 0.50
        matches.append("model_full")
    
    # Size match
    if mon.size and extracted_size:
        try:
            mon_size = int(float(mon.size))
            extracted_size_int = int(float(extracted_size))
            if mon_size == extracted_size_int:
                score += 0.15
                matches.append("size")
        except (ValueError, TypeError):
            pass
    
    if score > best_score:
        best_score = score
        best_match = mon
        best_method = "+".join(matches)
        if score >= 0.45:
            print(f"  New best: {mon.brand} {mon.model} = {score:.2f} ({best_method})")

print(f"\n=== FINAL BEST ===")
print(f"Best: {best_match.brand if best_match else 'None'} {best_match.model if best_match else ''}")
print(f"Score: {best_score:.2f}")
print(f"Method: {best_method}")

# Now simulate the logic
has_brand = "brand" in best_method
has_model = "model_full" in best_method or "model_partial" in best_method
has_monitor_context = is_included

print(f"\n=== DECISION LOGIC ===")
print(f"best_score >= 0.45: {best_score >= 0.45}")
print(f"has_brand: {has_brand}")
print(f"has_model: {has_model}")
print(f"has_monitor_context: {has_monitor_context}")

if best_score >= 0.45:
    if has_monitor_context and not has_model:
        print("\n  Should enter brand+size matching!")
        brand_lower = best_match.brand.lower()
        monitor_only_brands = ['hp', 'dell', 'lg', 'samsung', 'philips', 'benq', 'viewsonic', 'aoc', 'lenovo']
        print(f"  brand_lower: {brand_lower}")
        print(f"  in monitor_only_brands: {brand_lower in monitor_only_brands}")
        print(f"  extracted_size: {extracted_size}")
        
        if brand_lower in monitor_only_brands and extracted_size:
            print("\n  Searching for matching size monitors...")
            matching_size_monitors = []
            for mon in monitor_matcher.monitors:
                if mon.brand.lower() == brand_lower and mon.size:
                    try:
                        mon_size = int(float(mon.size))
                        extracted_size_int = int(float(extracted_size))
                        if mon_size == extracted_size_int:
                            matching_size_monitors.append(mon)
                    except (ValueError, TypeError):
                        pass
            
            print(f"  Found {len(matching_size_monitors)} matching monitors")
            if matching_size_monitors:
                print(f"  First match: {matching_size_monitors[0].brand} {matching_size_monitors[0].model}")
