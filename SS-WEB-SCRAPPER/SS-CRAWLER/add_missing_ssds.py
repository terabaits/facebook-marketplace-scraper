#!/usr/bin/env python3
"""Add missing SSD entries that are referenced in listings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def add_missing_ssds():
    """Add SSD entries that are referenced in listings but may not exist."""
    print("Checking for missing SSD entries...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Check if Kingston A400 480GB exists
        result = session.execute(
            text("""
                SELECT id, brand, model, capacity_gb 
                FROM ssd_reference 
                WHERE brand = 'Kingston' AND model = 'A400' AND capacity_gb = 480
            """)
        ).fetchone()
        
        if result:
            print(f"Kingston A400 480GB already exists (ID: {result[0]})")
        else:
            # Get max ID
            max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM ssd_reference")).scalar()
            new_id = max_id + 1
            
            # Add the SSD
            keywords = [
                "kingston", "a400", "kingston a400", "sa400s37",
                normalize_text("Kingston A400"),
                "480gb", "480 gb",
            ]
            
            session.execute(
                text("""
                    INSERT INTO ssd_reference 
                    (id, brand, model, interface, form_factor, capacity_gb, 
                     controller, configuration, has_dram, hmb, nand_brand, nand_type, 
                     layers, read_speed_mb, write_speed_mb, category, notes,
                     search_keywords, normalized_name)
                    VALUES (:id, :brand, :model, :interface, :form_factor, :capacity_gb,
                            :controller, :config, :has_dram, :hmb, :nand_brand, :nand_type,
                            :layers, :read_speed, :write_speed, :category, :notes,
                            :keywords, :normalized)
                """),
                {
                    "id": new_id,
                    "brand": "Kingston",
                    "model": "A400",
                    "interface": "SATA/AHCI",
                    "form_factor": '2.5"',
                    "capacity_gb": 480,
                    "controller": "Phison S11",
                    "config": "Single-core, 2-ch, 8-CE/ch",
                    "has_dram": False,
                    "hmb": "N/A",
                    "nand_brand": "Kioxia",
                    "nand_type": "TLC",
                    "layers": "32+",
                    "read_speed": 500,
                    "write_speed": 450,
                    "category": "Entry-Level SATA",
                    "notes": "QLC/SMI at higher cap.",
                    "keywords": keywords,
                    "normalized": normalize_text("Kingston A400")
                }
            )
            session.commit()
            print(f"[OK] Added Kingston A400 480GB (ID: {new_id})")
        
        # List all Kingston A400 SSDs to verify
        result = session.execute(
            text("SELECT id, brand, model, capacity_gb FROM ssd_reference WHERE brand = 'Kingston' AND model = 'A400' ORDER BY capacity_gb")
        ).fetchall()
        
        print("\nKingston A400 SSDs in database:")
        for r in result:
            print(f"  ID {r[0]}: {r[1]} {r[2]} {r[3]}GB")


if __name__ == "__main__":
    add_missing_ssds()
