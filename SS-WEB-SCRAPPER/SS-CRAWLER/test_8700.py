# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text, extract_cpu_tokens

config = AppConfig()
init_database(config.database)

db = get_db_manager()

# Check database for 8700 processors
with db.get_session() as session:
    cpus = session.query(CPUReferenceRepository.model).filter(
        CPUReferenceRepository.model.cpu_name.ilike('%8700%')
    ).limit(10).all()
    
    print("CPUs with '8700':")
    for cpu in cpus:
        if cpu.processor_number:
            norm = cpu.processor_number.lower().replace(' ', '').replace('-', '')
            print(f"  ID {cpu.id}: {cpu.cpu_name}")
            print(f"    Processor number: '{cpu.processor_number}'")
            print(f"    Normalized: '{norm}'")
            print()

# Test token extraction
text = """Procesors: AMD Ryzen r7 8700f - jauns;"""
normalized = normalize_text(text)
tokens = extract_cpu_tokens(text)

print("Text:", text)
print("Normalized:", normalized)
print("Tokens:", tokens)

# Check what tokens contain 8700
for token in tokens:
    if '8700' in token:
        print(f"\nToken with 8700: '{token}'")
        print(f"  Ends with 'f': {token.endswith('f')}")
        print(f"  Ends with 'g': {token.endswith('g')}")
