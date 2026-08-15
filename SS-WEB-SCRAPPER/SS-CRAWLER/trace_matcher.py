"""Trace the matcher logic"""
import sys
sys.path.insert(0, 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src')

import requests
from src.utils.config import AppConfig
from src.scraper.computer_scraper import ComputerScraper
from src.utils.text import normalize_text

# Fetch
url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

# Init scraper
config = AppConfig.from_yaml()
config.scraper.test_mode = True
scraper = ComputerScraper(config)
scraper.initialize()

# Get the parsed description
from src.scraper.computer_parser import ComputerListingParser
parser = ComputerListingParser(resp.text, url)
listing = parser.parse()

if listing:
    title = listing.title
    description = listing.description
    full_text = f"{title}\n{description}"
    normalized = normalize_text(full_text)
    
    print("FULL NORMALIZED TEXT:")
    print("="*60)
    print(normalized)
    print("="*60)
    
    # Check RAM line extraction
    print("\n\nRAM LINE EXTRACTION:")
    ram_keywords = ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas', 'operatīva']
    ram_line = ""
    lines = full_text.lower().split('\n')
    for i, line in enumerate(lines):
        for kw in ram_keywords:
            if kw in line:
                ram_line = line
                if i + 1 < len(lines):
                    ram_line += " " + lines[i + 1]
                break
        if ram_line:
            break
    print(f"RAM line: '{ram_line}'")
    print(f"'kingston' in ram_line: {'kingston' in ram_line}")
    print(f"'furry' in ram_line: {'furry' in ram_line}")
    print(f"'hyperx' in ram_line: {'hyperx' in ram_line}")
    
    # Check MB context
    print("\n\nMOTHERBOARD CONTEXT:")
    lines = full_text.lower().split('\n')
    mb_context_lines = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            mb_context_lines.append(line)
            skip_next = False
            continue
        if any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard']):
            mb_context_lines.append(line)
            if i + 1 < len(lines):
                mb_context_lines.append(lines[i + 1])
                skip_next = True
    mb_context = ' '.join(mb_context_lines) if mb_context_lines else normalized
    mb_context = normalize_text(mb_context)
    print(f"MB context: '{mb_context}'")
    print(f"'msi' in mb_context: {'msi' in mb_context}")
    print(f"'gaming' in mb_context: {'gaming' in mb_context}")
    print(f"'plus' in mb_context: {'plus' in mb_context}")
    print(f"'max' in mb_context: {'max' in mb_context}")
    print(f"'tomahawk' in mb_context: {'tomahawk' in mb_context}")
    
    # Now run the match
    print("\n\nRUNNING MATCH:")
    match_result = scraper.matcher.match(title, description, 500.0)
    
    print(f"\nRAM: {match_result.ram}")
    if match_result.ram:
        print(f"  ID: {match_result.ram.get('id') if isinstance(match_result.ram, dict) else match_result.ram.id}")
    print(f"  Confidence: {match_result.ram_confidence}")
    print(f"  Method: {match_result.ram_method}")
    
    print(f"\nMB: {match_result.motherboard}")
    if match_result.motherboard:
        print(f"  ID: {match_result.motherboard.get('id') if isinstance(match_result.motherboard, dict) else match_result.motherboard.id}")
    print(f"  Confidence: {match_result.motherboard_confidence}")
    print(f"  Method: {match_result.motherboard_method}")
