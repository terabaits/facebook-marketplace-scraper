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
    # Find Ryzen 5 1600
    cpus = session.query(CPUReferenceRepository.model).filter(
        CPUReferenceRepository.model.cpu_name.ilike('%ryzen%1600%')
    ).limit(10).all()
    
    print("CPUs matching 'ryzen 1600':")
    for cpu in cpus:
        print(f"  ID {cpu.id}: {cpu.cpu_name}")
        print(f"    Processor number: '{cpu.processor_number}'")
        if cpu.processor_number:
            norm = cpu.processor_number.lower().replace(' ', '').replace('-', '')
            print(f"    Normalized: '{norm}'")
        print()
    
    # Also check for ID 1509
    cpu_1509 = session.query(CPUReferenceRepository.model).filter_by(id=1509).first()
    if cpu_1509:
        print(f"ID 1509: {cpu_1509}")
        print(f"  Name: {cpu_1509.cpu_name}")
        print(f"  Processor number: '{cpu_1509.processor_number}'")
        if cpu_1509.processor_number:
            norm = cpu_1509.processor_number.lower().replace(' ', '').replace('-', '')
            print(f"  Normalized: '{norm}'")
