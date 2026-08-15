"""Direct test of monitor matching with debug output"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import logging
logging.basicConfig(level=logging.DEBUG)

from src.scraper.computer_scraper import ComputerScraper
from src.utils.config import AppConfig

config = AppConfig.from_yaml()

# Get monitors from database  
scraper = ComputerScraper(config)
scraper.initialize()
monitor_matcher = scraper.matcher.monitor_matcher

# Test with exact text from listing
title = "Datori un orgtehnika/Datori/ Pārdod"
description = """Pārdodu PC
Proccesor Xeon e5-2680 v4 14 Cores 28 Treads
Video - Rx580 8gb
Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz
SSD - 1x SSD 128gb / 1x SSD 500gb
Līdzi dodu HDD 1-Tb
Var dabūt nedaudz lētak ar RAM 1x 16Gb
Monitors HP 24 collas dāvana"""

print("=== TESTING MATCH ===")
print(f"Title: {title}")
print(f"Description:\n{description}")
print()

result = monitor_matcher.match_listing(title, description)
print(f"\n=== RESULT ===")
print(f"Monitor: {result[0]}")
print(f"Confidence: {result[1]}")
print(f"Method: {result[2]}")
