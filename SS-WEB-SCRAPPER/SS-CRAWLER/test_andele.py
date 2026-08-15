#!/usr/bin/env python3
"""Test script for Andele scraper."""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER')

from src.scraper.andele_scraper import AndeleScraper

url = "https://www.andelemandele.lv/perle/15751593/pny-gtx-1650/"

print("Testing Andele Scraper...")
print(f"URL: {url}")
print("-" * 50)

scraper = AndeleScraper(dry_run=True)
result = scraper.test_url(url, 'gpu')

import json
print(json.dumps(result, indent=2, ensure_ascii=False))
