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
    # Search for CPUs with "1600" in name
    print("=== CPUs with '1600' ===")
    cpus = session.query(CPUReferenceRepository.model).filter(
        CPUReferenceRepository.model.cpu_name.ilike('%1600%')
    ).limit(20).all()
    
    for cpu in cpus:
        print(f"ID {cpu.id}: {cpu.cpu_name}")
        print(f"  Processor number: '{cpu.processor_number}'")
        if cpu.processor_number:
            norm = cpu.processor_number.lower().replace(' ', '').replace('-', '')
            print(f"  Normalized: '{norm}'")
        print()
