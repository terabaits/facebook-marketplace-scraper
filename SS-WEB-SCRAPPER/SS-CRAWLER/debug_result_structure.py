# -*- coding: utf-8 -*-
"""Debug result.ssd structure."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    ssd = SSDReferenceRepository.get_by_id(session, 453)

print("SSD ID 453 structure:")
print(f"  Type: {type(ssd)}")
print(f"  Has model_dump: {hasattr(ssd, 'model_dump')}")
print(f"  Has __dict__: {hasattr(ssd, '__dict__')}")

if hasattr(ssd, 'model_dump'):
    dumped = ssd.model_dump()
    print(f"\n  model_dump() result type: {type(dumped)}")
    print(f"  Keys: {list(dumped.keys())[:5]}")
    print(f"  'name' in dumped: {'name' in dumped}")
    if 'name' in dumped:
        print(f"  dumped['name']: {dumped['name']}")

if hasattr(ssd, '__dict__'):
    print(f"\n  __dict__ keys: {list(ssd.__dict__.keys())[:5]}")
