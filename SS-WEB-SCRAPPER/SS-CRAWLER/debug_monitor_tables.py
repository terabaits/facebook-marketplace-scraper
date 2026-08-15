# -*- coding: utf-8 -*-
"""Debug monitor detection for pbdhn."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.utils.text import normalize_text
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

# List tables
with db.get_session() as session:
    from sqlalchemy import text, inspect
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()
    print("Tables in database:")
    for t in sorted(tables):
        print(f"  {t}")
    
    # Check for monitor-related tables
    monitor_tables = [t for t in tables if 'monitor' in t.lower()]
    print(f"\nMonitor-related tables: {monitor_tables}")
    
    # Try to load from any monitor table found
    monitors = []
    from src.models.schemas import MonitorReference
    
    for table_name in monitor_tables:
        try:
            result = session.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
            rows = list(result)
            print(f"\nTable '{table_name}' has {len(rows)} sample rows")
            if rows:
                print(f"  Columns: {list(rows[0]._mapping.keys())}")
                print(f"  First row sample: {dict(rows[0]._mapping)}")
        except Exception as e:
            print(f"Error querying {table_name}: {e}")
