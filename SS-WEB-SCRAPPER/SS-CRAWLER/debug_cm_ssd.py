# -*- coding: utf-8 -*-
"""Debug computer_matcher SSD logic."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)
    
    # Check what SSD ID 587 is
    ssd_587 = next((s for s in ssds if s.id == 587), None)
    if ssd_587:
        print(f"SSD ID 587: {ssd_587.brand} {ssd_587.model}")
        print(f"  Normalized: {ssd_587.normalized_name}")
        print(f"  Keywords: {ssd_587.search_keywords}")
    
    # Check if there's a pattern that would match "SSD" alone
    print("\nSSDs with generic 'SSD' model:")
    for ssd in ssds:
        if ssd.model.lower() == 'ssd':
            print(f"  ID {ssd.id}: {ssd.brand} {ssd.model}")
