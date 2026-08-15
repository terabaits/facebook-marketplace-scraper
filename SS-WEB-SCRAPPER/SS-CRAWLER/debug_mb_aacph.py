# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MotherboardRepository
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    mbs = MotherboardRepository.get_all(session)

matcher = MotherboardMatcher(mbs)

# Test aacph
text = """Мат. пл. Gigabyte H310M S2H 2.0"""

title = "Datori un orgtehnika/Datori/ Pārdod"
desc = """Itel Core i5-9400f Coffee Lake 2.90 Ghz
Мат. пл. Gigabyte H310M S2H 2.0
G. Skill Ddr4-2666 32gb"""

print("Testing aacph motherboard matching...")

# Check what's in the database for H310M
print("\n=== H310M Motherboards ===")
for mb in mbs:
    if mb.model and 'h310m' in mb.model.lower():
        print(f"  ID {mb.id}: {mb.brand} {mb.model}")

# Direct match test
result = matcher.match(text, "")
print(f"\nDirect match result: {result.motherboard}")
if result.motherboard:
    print(f"  ID: {result.motherboard.id}")
    print(f"  Brand: {result.motherboard.brand}")
    print(f"  Model: {result.motherboard.model}")
    print(f"  Method: {result.method}")
