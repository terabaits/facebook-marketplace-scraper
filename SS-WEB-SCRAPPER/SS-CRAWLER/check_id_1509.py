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
    # Check ID 1509
    cpu = session.query(CPUReferenceRepository.model).filter_by(id=1509).first()
    if cpu:
        print(f"ID 1509: {cpu}")
        print(f"  Name: {cpu.cpu_name}")
        print(f"  Processor number: {cpu.processor_number}")
    else:
        print("ID 1509: Not found")
    
    # Check ID 3957 (5160)
    cpu = session.query(CPUReferenceRepository.model).filter_by(id=3957).first()
    if cpu:
        print(f"\nID 3957 (5160): {cpu}")
        print(f"  Name: {cpu.cpu_name}")
        print(f"  Processor number: {cpu.processor_number}")
