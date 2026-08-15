# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.utils.config import AppConfig

config = AppConfig()
print("Initializing database...")
init_database(config.database)
print("Getting DB manager...")
db = get_db_manager()
print("Getting session...")
with db.get_session() as session:
    print("Got session!")
print("Done!")
