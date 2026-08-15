# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import MonitorRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    monitors = MonitorRepository.get_all(session)

# Test monitor context
monitor_context = "monitors hp 24 collas dāvana"

print("Checking HP 24\" monitors:")
for mon in monitors:
    if mon.brand and mon.brand.lower() == 'hp' and mon.size == '24':
        model_clean = normalize_text(mon.model)
        in_context = model_clean in monitor_context
        print(f"  {mon.model}")
        print(f"    Normalized: '{model_clean}'")
        print(f"    In context: {in_context}")
        if in_context:
            print("    *** MATCH ***")
