# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository
from src.scraper.cpu_matcher import CPUMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cpus = CPURepository.get_all(session)
    matcher = CPUMatcher(cpus)
    
    # Test fgfbp CPU
    text = "pardod datoru procesors intel core i514400f"
    normalized = normalize_text(text)
    
    print(f"Text: {text}")
    print(f"Normalized: {normalized}\n")
    
    # Find CPUs with 14400
    print("CPUs with '14400':")
    for cpu in cpus:
        if '14400' in cpu.cpu_name.lower():
            print(f"  ID {cpu.id}: {cpu.cpu_name} (processor_number: {cpu.processor_number})")
    
    # Match
    result = matcher.match(text)
    print(f"\nMatched: {result.cpu.cpu_name if result.cpu else 'None'} (ID: {result.cpu.id if result.cpu else 'N/A'})")
    print(f"Method: {result.method}")
    print(f"Confidence: {result.confidence}")
    
    # Check tokens
    print(f"\nNormalized tokens: {normalized.split()}")
    for token in normalized.split():
        if '14400' in token:
            print(f"  Token with 14400: '{token}'")
            print(f"  Ends with 'f': {token.endswith('f')}")
