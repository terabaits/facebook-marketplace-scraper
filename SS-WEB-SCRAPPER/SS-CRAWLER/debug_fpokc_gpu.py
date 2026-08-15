# -*- coding: utf-8 -*-
"""Debug fpokc GPU matching - why is it matching?"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.scraper.matcher import GPUMatcher
from src.database.connection import get_db_manager, init_database
from src.database.repository import GPUReferenceRepository
from src.utils.text import normalize_text, extract_gpu_tokens
from src.utils.config import AppConfig
import re

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

# fpokc text
text = """Pārdod spēļu datoru.
Procesors: i5-13600
Mātesplate: Gigabyte B760M Gaming X AX DDR4
Operatīvā atmiņa: DDR4 Kingston HyperX Fury 32GB 3600MHz RGB
Cietie diski: SSD Crucial MX500 1TB
Barošanas bloks: OCZ ModXStream Pro 500W
Korpuss: Fractal Design Focus G Mini"""

print("=== fpokc GPU Debug ===")
normalized = normalize_text(text)
print(f"Normalized:\n{normalized}\n")

# Check what patterns would remove
print("=== Pattern Removal ===")
text_lower = normalized.lower()

# Original patterns
print(f"Original: {text_lower[:100]}...")

# CPU patterns
cpu_patterns = [
    r'i[3579]\s*-?\s*\d{4,5}',
    r'ryzen\s*\d?\s*\d{3,4}',
    r'r[3579]\s*\d{3,4}',
    r'xeon\s*[ew]?\d*-?\d{4}',
]
text_for_gpu = text_lower
for pattern in cpu_patterns:
    text_for_gpu = re.sub(pattern, '', text_for_gpu, flags=re.IGNORECASE)
text_for_gpu = re.sub(r'\s+', ' ', text_for_gpu).strip()
print(f"After CPU removal: {text_for_gpu[:100]}...")

# MB chipset patterns
mb_patterns = [
    r'\b[bxzab]\d{3,4}[mh]?\b',
    r'\bh\d{3}[mh]?\b',
]
for pattern in mb_patterns:
    text_for_gpu = re.sub(pattern, '', text_for_gpu, flags=re.IGNORECASE)
text_for_gpu = re.sub(r'\s+', ' ', text_for_gpu).strip()
print(f"After MB removal: {text_for_gpu[:100]}...")

# Check if "760" or "500" still present
if '760' in text_for_gpu:
    print("\n⚠️ '760' still in text - will match GTX 760")
if '500' in text_for_gpu:
    print("⚠️ '500' still in text - will match various GPUs")
    # Find positions
    for i, char in enumerate(text_for_gpu):
        if char == '5' and i+2 < len(text_for_gpu) and text_for_gpu[i:i+3] == '500':
            context = text_for_gpu[max(0,i-20):min(len(text_for_gpu), i+20)]
            print(f"  '500' at pos {i}: ...{context}...")
