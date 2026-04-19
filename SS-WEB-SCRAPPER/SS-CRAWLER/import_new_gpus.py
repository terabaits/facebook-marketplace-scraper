"""Import new GPUs from cards.csv without removing existing data."""
import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text
import csv

# New GPUs to add
new_gpus = [
    ("AMD", "Radeon RX 9060 XT"),
    ("AMD", "Radeon RX 9070 GRE"),
    ("AMD", "Radeon RX 9070"),
    ("AMD", "Radeon RX 9070 XT"),
]

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    added = 0
    skipped = 0
    
    for vendor, model in new_gpus:
        # Check if already exists
        result = session.execute(
            text("SELECT id FROM gpu_reference WHERE model = :model"),
            {"model": model}
        ).fetchone()
        
        if result:
            print(f"Skipping (already exists): {model}")
            skipped += 1
            continue
        
        # Generate normalized name and search keywords
        from src.utils.text import normalize_text
        normalized = normalize_text(model).replace(' ', '')
        
        # Common search variants
        search_keywords = [normalized]
        # Add rx variant
        if ' rx ' in model.lower():
            search_keywords.append(model.lower().replace(' ', ''))
        
        # Insert new GPU
        session.execute(text("""
            INSERT INTO gpu_reference (vendor, model, normalized_name, search_keywords, vram_gb, year_released)
            VALUES (:vendor, :model, :normalized_name, :search_keywords, NULL, 2025)
        """), {
            "vendor": vendor,
            "model": model,
            "normalized_name": normalized,
            "search_keywords": search_keywords
        })
        
        print(f"Added: {model}")
        added += 1
    
    session.commit()
    print(f"\nSummary: Added {added}, Skipped {skipped}")
    
    # Show total count
    result = session.execute(text("SELECT COUNT(*) FROM gpu_reference"))
    count = result.fetchone()[0]
    print(f"Total GPUs in database: {count}")
