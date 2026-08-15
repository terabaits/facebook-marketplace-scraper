import sys
sys.path.insert(0, 'src')
from src.database.connection import get_db_manager
from src.database.repository import SSDReferenceRepository

# Initialize database
from src.database.connection import init_database
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)
    
    # Find CS1030
    for ssd in ssds:
        if ssd.id == 1381:
            print(f"SSD ID 1381:")
            print(f"  Brand: {ssd.brand}")
            print(f"  Model: {ssd.model}")
            print(f"  Capacity: {ssd.capacity_gb}")
            print(f"  Search keywords: {ssd.search_keywords}")
            break
