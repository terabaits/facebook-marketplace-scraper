# -*- coding: utf-8 -*-
"""Quick debug of issues"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPURepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    cpus = CPURepository.get_all(session)
    print(f"Total CPUs: {len(cpus)}")
    print("\nCPUs with 14400:")
    for cpu in cpus:
        if '14400' in cpu.cpu_name:
            print(f"  ID {cpu.id}: {cpu.cpu_name}")
