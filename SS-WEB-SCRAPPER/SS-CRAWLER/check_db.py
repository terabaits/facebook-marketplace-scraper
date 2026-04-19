import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    # Check the listing in database
    result = session.execute(text("SELECT * FROM listings WHERE listing_id = 'nhdnf'")).fetchone()
    if result:
        print('Listing nhdnf in database:')
        print(f'  matched_gpu_id: {result.matched_gpu_id}')
        print(f'  confidence_score: {result.confidence_score}')
        print(f'  match_method: {result.match_method}')
        
        # Get GPU name
        if result.matched_gpu_id:
            gpu = session.execute(
                text("SELECT model FROM gpu_reference WHERE id = :id"),
                {"id": result.matched_gpu_id}
            ).fetchone()
            if gpu:
                print(f'  GPU: {gpu.model}')
    else:
        print('Listing nhdnf not found in database')
    
    print()
    print('RX 9070 GPUs in database:')
    result = session.execute(text("SELECT id, model, vram_gb FROM gpu_reference WHERE model LIKE '%9070%' ORDER BY id"))
    for row in result:
        vram_gb = row.vram_gb // 1024 if row.vram_gb else 0
        print(f'  ID {row.id}: {row.model} ({vram_gb}GB)')
