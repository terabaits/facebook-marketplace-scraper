import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.utils.config import AppConfig
from src.database.connection import get_session, init_database
from sqlalchemy import text

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    # Check if RX 9070 XT is in database
    result = session.execute(text("SELECT model, vram_gb FROM gpu_reference WHERE model ILIKE '%9070%'"))
    print('RX 9070 in database:')
    for row in result:
        print(f"  {row.model}: {row.vram_gb/1024 if row.vram_gb else 0} GB")
    
    # Also check for 650
    result = session.execute(text("SELECT model, vram_gb FROM gpu_reference WHERE model ILIKE '%gtx 650%'"))
    print()
    print('GTX 650 in database:')
    for row in result:
        print(f"  {row.model}: {row.vram_gb/1024 if row.vram_gb else 0} GB")
