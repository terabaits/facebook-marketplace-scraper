# -*- coding: utf-8 -*-
"""Debug gccgg PSU matching."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import PSURepository
from src.scraper.psu_matcher import PSUMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    psus = PSURepository.get_all(session)

matcher = PSUMatcher(psus)

# gccgg text
text = """Barošanas bloks: Corsair VS650 650W"""

print("=== gccgg PSU Debug ===")
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Check what PSUs have "corsair" and "vs650"
print("\n=== Corsair PSUs ===")
for psu in psus:
    if 'corsair' in psu.brand.lower():
        if 'vs' in psu.model.lower() or 'vs' in psu.name.lower():
            print(f"ID {psu.id}: {psu.name} - {psu.wattage}W")

# Match
print("\n=== PSU Match ===")
result = matcher.match_listing(text, 460.0)
if result.psu:
    print(f"Matched: ID {result.psu.id} - {result.psu.name}")
    print(f"Method: {result.method}")
else:
    print("No PSU matched")
