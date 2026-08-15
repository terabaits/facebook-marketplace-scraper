# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository
from src.scraper.cpu_matcher import CPUMatcher
from src.utils.config import AppConfig
from src.utils.text import extract_cpu_tokens, normalize_text

config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)

matcher = CPUMatcher(cpus)

# Test text from pbdhn.html
text = """CPU - AMD R5 1600 3.2 GHz"""

normalized = normalize_text(text)
print("Text:", text)
print("Normalized:", normalized)
print()

# Extract tokens
tokens = extract_cpu_tokens(text)
print("Tokens:", tokens)
print()

# Check which CPUs have "1600" in their processor_number
print("CPUs with '1600' in processor_number:")
for cpu in cpus:
    if cpu.processor_number and '1600' in cpu.processor_number.lower():
        proc_num_lower = cpu.processor_number.lower().replace(' ', '').replace('-', '')
        print(f"  ID {cpu.id}: {cpu.cpu_name}")
        print(f"    Processor number: '{cpu.processor_number}'")
        print(f"    Normalized: '{proc_num_lower}'")
        
        # Check if it would match "r51600"
        for token in tokens:
            if proc_num_lower in token.lower():
                print(f"    MATCHES token: '{token}'")
        print()
