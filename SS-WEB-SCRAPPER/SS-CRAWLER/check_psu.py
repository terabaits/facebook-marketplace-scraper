# Check PSU ID 8593
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    from src.database.models import PSUReference
    psu = session.query(PSUReference).filter(PSUReference.id == 8593).first()
    if psu:
        print(f"ID {psu.id}: {psu.name}")
        print(f"Wattage: {psu.wattage}")
        print(f"Keywords: {psu.search_keywords}")
    else:
        print("PSU ID 8593 not found")
