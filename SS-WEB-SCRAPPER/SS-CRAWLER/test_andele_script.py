#!/usr/bin/env python3
"""Test Andele scraper and save results."""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER')

from src.scraper.andele_scraper import AndeleScraper
import json

url = "https://www.andelemandele.lv/perle/15751593/pny-gtx-1650/"

try:
    scraper = AndeleScraper(dry_run=True)
    result = scraper.test_url(url, 'gpu')
    
    with open('test_andele_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("SUCCESS")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
except Exception as e:
    import traceback
    error_info = {
        'error': str(e),
        'traceback': traceback.format_exc()
    }
    with open('test_andele_error.json', 'w', encoding='utf-8') as f:
        json.dump(error_info, f, indent=2)
    print("FAILED:", str(e))
