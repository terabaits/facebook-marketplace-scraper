# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.utils.config import AppConfig
from src.utils.text import normalize_text, extract_gpu_tokens

config = AppConfig()
init_database(config.database)

db = get_db_manager()

with db.get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

# Test text
text = """Videokarte: Powercolor red devil RX6800XT 16gb - lietota;"""

print("Testing GPU matching...")
result = matcher.match(text, "")
print(f"Result: {result}")

# Check if RX 6800 XT exists
print("\n=== GPUs with '6800' ===")
for gpu in gpus:
    if '6800' in gpu.model.lower():
        print(f"ID {gpu.id}: {gpu.model}")
        print(f"  Normalized: '{normalize_text(gpu.model)}'")
        print()
