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

# Test
monitor_context = "monitors hp 24 collas dāvana"

print("Checking HP 27mq specifically:")
for mon in monitors:
    if mon.brand and mon.brand.lower() == 'hp' and mon.model == 'HP 27mq':
        model_clean = normalize_text(mon.model)
        print(f"  model_clean: '{model_clean}'")
        print(f"  in monitor_context: {model_clean in monitor_context}")
        
        # Check prefix
        if len(model_clean) >= 4:
            print(f"  Checking prefixes:")
            for i in range(len(model_clean), 3, -1):
                model_prefix = model_clean[:i]
                print(f"    '{model_prefix}' in monitor_context: {model_prefix in monitor_context}")
                if model_prefix in monitor_context:
                    print(f"    *** Would match with prefix: '{model_prefix}'")
                    break
