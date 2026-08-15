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
    # Check all Ryzen CPUs
    cpus = session.query(CPUReferenceRepository.model).filter(
        CPUReferenceRepository.model.cpu_name.ilike('%ryzen%1600%')
    ).all()
    
    print("All CPUs with 'Ryzen' and '1600':")
    for cpu in cpus:
        print(f"  ID {cpu.id}: {cpu.cpu_name}")
        print(f"    Processor number: '{cpu.processor_number}'")
        if cpu.processor_number:
            norm = cpu.processor_number.lower().replace(' ', '').replace('-', '')
            print(f"    Normalized: '{norm}'")
        print()
    
    # Check for ID 1509 specifically
    print("\nID 1509:")
    cpu = session.query(CPUReferenceRepository.model).filter_by(id=1509).first()
    if cpu:
        print(f"  {cpu}")
    else:
        print("  Not found!")
        
    # Check for ID 3957 (5160)
    print("\nID 3957 (5160):")
    cpu = session.query(CPUReferenceRepository.model).filter_by(id=3957).first()
    if cpu:
        print(f"  {cpu}")
