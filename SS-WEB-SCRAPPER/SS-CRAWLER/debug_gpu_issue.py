# -*- coding: utf-8 -*-
"""Debug GPU matching issue."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository
from src.scraper.matcher import GPUMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

# fpokc text
text = """Procesors: i5-13600"""

print("Testing GPU matching for 'i5-13600'...")
normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Check what GPUs have "760" in model
print("\n=== GPUs with '760' in model ===")
for gpu in gpus:
    if '760' in gpu.model:
        print(f"  ID {gpu.id}: {gpu.model}")

# Check match
result = matcher.match_listing(text, 500.0)
print(f"\nMatch result:")
if result.gpu:
    print(f"  GPU: {result.gpu.model} (ID: {result.gpu.id})")
    print(f"  Method: {result.method}")
else:
    print("  No GPU matched")
