import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    print('GT 740 variants in database:')
    print('-' * 40)
    result = session.execute(text("SELECT model, vram_gb FROM gpu_reference WHERE model ILIKE '%gt 740%' ORDER BY vram_gb"))
    found = False
    for row in result:
        vram_gb = row.vram_gb / 1024 if row.vram_gb else 'N/A'
        print(f'{row.model}: {vram_gb} GB')
        found = True
    
    if not found:
        print('No GT 740 found')
        
    print()
    print('Checking all 740 models...')
    result = session.execute(text("SELECT model, vram_gb FROM gpu_reference WHERE model ILIKE '%740%' ORDER BY vram_gb"))
    for row in result:
        vram_gb = row.vram_gb / 1024 if row.vram_gb else 'N/A'
        print(f'{row.model}: {vram_gb} GB')
