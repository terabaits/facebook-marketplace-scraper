"""Update VRAM for new AMD GPUs."""
import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text

config = AppConfig.from_yaml()
init_database(config.database)

# VRAM info for new GPUs (in MB)
vram_updates = {
    "Radeon RX 9060 XT": 16384,   # 16 GB
    "Radeon RX 9070 GRE": 12288,  # 12 GB
    "Radeon RX 9070": 16384,      # 16 GB
    "Radeon RX 9070 XT": 16384,   # 16 GB
}

with get_session() as session:
    for model, vram_mb in vram_updates.items():
        result = session.execute(
            text("UPDATE gpu_reference SET vram_gb = :vram WHERE model = :model"),
            {"vram": vram_mb, "model": model}
        )
        print(f"Updated {model}: {vram_mb} MB ({vram_mb//1024} GB)")
    
    session.commit()
    print("\nVRAM update complete!")

# Verify
with get_session() as session:
    for model in vram_updates.keys():
        result = session.execute(
            text("SELECT model, vram_gb FROM gpu_reference WHERE model = :model"),
            {"model": model}
        ).fetchone()
        if result:
            print(f"{result.model}: {result.vram_gb} MB")
