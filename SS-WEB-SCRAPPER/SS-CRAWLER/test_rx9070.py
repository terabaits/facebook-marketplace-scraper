import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.scraper.matcher import GPUMatcher
from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    result = session.execute(text('SELECT * FROM gpu_reference'))
    from src.models.schemas import GPUReference
    gpus = []
    for row in result:
        gpus.append(GPUReference(
            id=row.id,
            vendor=row.vendor,
            model=row.model,
            vram_gb=row.vram_gb,
            year_released=row.year_released,
            normalized_name=row.normalized_name,
            search_keywords=row.search_keywords
        ))

matcher = GPUMatcher(gpus)

# Simulate the actual listing
title = 'Asus Prime Radeon'
desc = 'Asus Prime Radeon RX 9070 XT OC Edition 16Gb'
price_text = 'EUR 650.00'

print('Testing RX 9070 XT matching:')
print('Title:', title)
print('Desc:', desc)
print('Price:', price_text)
print()

# Test match
result = matcher.match(title, desc, 16000)
gpu_name = result.gpu.model if result.gpu else 'None'
print('Match:', gpu_name)
print('Confidence:', f'{result.confidence:.1%}')
print('Method:', result.method)
print()

# Check candidates
candidates = matcher.get_candidates(f'{title} {desc}', limit=5, vram_mb=16000)
print('Top candidates:')
for gpu, score in candidates:
    vram_info = f'{gpu.vram_gb/1024:.0f}GB' if gpu.vram_gb else 'N/A'
    print(f'  - {gpu.model} ({vram_info}): {score:.2%}')
