# Quick test
import sys
sys.path.insert(0, 'src')

print("Starting test...")

from src.database.connection import get_db_manager, init_database
from src.utils.config import AppConfig

config = AppConfig()
print("Config loaded")

init_database(config.database)
print("Database initialized")

db = get_db_manager()
print("DB manager got")

with db.get_session() as session:
    print("Session opened")
    from src.database.repository import CPURepository
    cpus = CPURepository.get_all(session)
    print(f"Loaded {len(cpus)} CPUs")
    
    # Check i5-14400 CPUs
    print("\nCPUs with 14400:")
    for cpu in cpus:
        if '14400' in cpu.cpu_name:
            print(f"  ID {cpu.id}: {cpu.cpu_name}")

print("\nDone!")
