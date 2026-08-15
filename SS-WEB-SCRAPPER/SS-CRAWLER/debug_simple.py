# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'src')

from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
import re

# Mock ComputerMatcher with minimal setup
class MockSSD:
    def __init__(self, id, brand, model, capacity_gb):
        self.id = id
        self.brand = brand
        self.model = model
        self.capacity_gb = capacity_gb
        self.normalized_name = normalize_text(f"{brand} {model}")
        self.search_keywords = [self.normalized_name, brand.lower(), model.lower()]

# Test texts
test_cases = [
    ("SSD Crucial MX500 1TB", "fpokc SSD"),
    ("Bez videokartes", "No GPU check"),
    ("DDR4 Patriot Viper Steel 8GB", "pbdhn RAM"),
]

for text, label in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {label}")
    print(f"Text: '{text}'")
    normalized = normalize_text(text)
    print(f"Normalized: '{normalized}'")
    
    # Check brand_near_ssd logic
    if "SSD" in label:
        text_lower = normalized.lower()
        ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'intel', 'adata']
        
        print("\nChecking brand_near_ssd logic:")
        for brand in ssd_brand_keywords:
            if brand in text_lower:
                brand_pos = text_lower.find(brand)
                window_start = max(0, brand_pos - 40)
                window_end = min(len(text_lower), brand_pos + 40)
                window = text_lower[window_start:window_end]
                has_ssd_kw = any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2', 'solid'])
                print(f"  Brand '{brand}' at pos {brand_pos}, window has SSD kw: {has_ssd_kw}")
                print(f"    Window: '{window}'")
