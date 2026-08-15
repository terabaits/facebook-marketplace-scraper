#!/usr/bin/env python3
"""Debug script for fcddo listing to check SSD matching."""

import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

from src.scraper.ssd_matcher import SSDMatcher
from src.models.schemas import SSDReference
import re

# Sample SSDs from database - include Crucial 120GB
sample_ssds = [
    SSDReference(id=1, brand="Kingston", model="A400", capacity_gb=120, type="SATA", price=35.0, search_keywords=["kingston a400", "a400"], normalized_name="kingston a400"),
    SSDReference(id=2, brand="Kingston", model="A400", capacity_gb=240, type="SATA", price=35.0, search_keywords=["kingston a400", "a400"], normalized_name="kingston a400"),
    SSDReference(id=3, brand="Kingston", model="A400", capacity_gb=480, type="SATA", price=45.0, search_keywords=["kingston a400", "a400"], normalized_name="kingston a400"),
    SSDReference(id=4, brand="Crucial", model="MX500", capacity_gb=120, type="SATA", price=48.0, search_keywords=["crucial mx500", "mx500"], normalized_name="crucial mx500"),
    SSDReference(id=5, brand="Crucial", model="MX500", capacity_gb=250, type="SATA", price=48.0, search_keywords=["crucial mx500", "mx500"], normalized_name="crucial mx500"),
    SSDReference(id=6, brand="Crucial", model="MX500", capacity_gb=500, type="SATA", price=65.0, search_keywords=["crucial mx500", "mx500"], normalized_name="crucial mx500"),
    SSDReference(id=7, brand="Crucial", model="P3", capacity_gb=500, type="NVMe", price=50.0, search_keywords=["crucial p3", "p3"], normalized_name="crucial p3"),
    SSDReference(id=8, brand="Crucial", model="P3", capacity_gb=1000, type="NVMe", price=75.0, search_keywords=["crucial p3", "p3"], normalized_name="crucial p3"),
    SSDReference(id=9, brand="Samsung", model="870 EVO", capacity_gb=250, type="SATA", price=55.0, search_keywords=["samsung 870 evo", "870 evo"], normalized_name="samsung 870 evo"),
    SSDReference(id=10, brand="ADATA", model="SU650", capacity_gb=240, type="SATA", price=32.0, search_keywords=["adata su650", "su650"], normalized_name="adata su650"),
]

matcher = SSDMatcher(sample_ssds)

# Test texts - what might be in the fcddo listing
test_texts = [
    "Datori un orgtehnika/Datori/ Pardod",
    "Pardod datoru ar Crucial 120GB SSD",
    "Crucial 120 GB SSD",
    "120GB Crucial SSD",
    "Crucial SSD 120GB",
]

print("=" * 80)
print("SSD MATCHING TEST FOR fcddo LISTING")
print("=" * 80)

for text in test_texts:
    print("\nInput text: '%s'" % text)
    
    # Extract capacity manually to debug
    patterns = [
        r'(\d+)\s*TB\b',
        r'(\d+)\s*GB\b',
        r'(\d+)\s*T\b',
        r'(\d+)\s*G\b',
    ]
    extracted_capacity = None
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                val = int(match)
                if 'tb' in pattern.lower():
                    val = val * 1000
                extracted_capacity = val
                break
            except ValueError:
                continue
    print("  Extracted capacity: %s" % extracted_capacity)
    
    result = matcher.match_listing(text)
    if result.ssd:
        print("  MATCHED: %s %s (%sGB)" % (result.ssd.brand, result.ssd.model, result.ssd.capacity_gb))
        print("  Confidence: %.1f%%" % (result.confidence * 100))
        print("  Method: %s" % result.method)
    else:
        print("  NO MATCH - Would use generic fallback")
