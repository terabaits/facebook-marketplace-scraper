# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    # Get all CPUs
    cpus = session.query(CPUReferenceRepository.model).all()
    
    # Filter for Ryzen
    ryzen_cpus = [c for c in cpus if c.cpu_name and 'ryzen' in c.cpu_name.lower() and '1600' in c.cpu_name.lower()]
    
    print(f"Found {len(ryzen_cpus)} Ryzen CPUs with '1600'")
    for cpu in ryzen_cpus:
        print(f"ID {cpu.id}: {cpu.cpu_name}")
