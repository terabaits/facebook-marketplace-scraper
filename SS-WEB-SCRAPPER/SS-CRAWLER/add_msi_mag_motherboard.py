#!/usr/bin/env python3
"""Add MSI MAG motherboard to database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def add_msi_mag_motherboard():
    """Add MSI MAG motherboard."""
    print("Adding MSI MAG motherboard...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    # Common MSI MAG motherboards
    motherboards = [
        {
            "brand": "MSI",
            "model": "MAG Z370 TOMAHAWK",
            "socket": "LGA1151",
            "chipset": "Z370",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI",
            "model": "MAG B550 TOMAHAWK",
            "socket": "AM4",
            "chipset": "B550",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI", 
            "model": "MAG B760 TOMAHAWK WIFI",
            "socket": "LGA1700",
            "chipset": "B760",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI",
            "model": "MAG B660 TOMAHAWK WIFI DDR4",
            "socket": "LGA1700",
            "chipset": "B660",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI",
            "model": "MAG X570 TOMAHAWK WIFI",
            "socket": "AM4",
            "chipset": "X570",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI",
            "model": "MAG B650 TOMAHAWK WIFI",
            "socket": "AM5",
            "chipset": "B650",
            "form_factor": "ATX",
            "ram_slots": 4
        },
        {
            "brand": "MSI",
            "model": "MAG Z790 TOMAHAWK WIFI",
            "socket": "LGA1700",
            "chipset": "Z790",
            "form_factor": "ATX",
            "ram_slots": 4
        },
    ]
    
    with get_session() as session:
        added = 0
        
        for mb in motherboards:
            # Check if exists
            result = session.execute(
                text("SELECT id FROM motherboard_models WHERE brand = :brand AND model = :model"),
                {"brand": mb["brand"], "model": mb["model"]}
            ).fetchone()
            
            if result:
                print(f"  Already exists: {mb['brand']} {mb['model']} (ID: {result[0]})")
                continue
            
            # Generate keywords
            keywords = [
                mb["brand"].lower(),
                mb["model"].lower().replace(" ", ""),
                mb["model"].lower(),
                "msi mag",
                "mag",
                "tomahawk",
                mb["chipset"].lower(),
                mb["socket"].lower(),
            ]
            
            session.execute(
                text("""
                    INSERT INTO motherboard_models 
                    (brand, model, socket, chipset, form_factor, ram_slots, 
                     normalized_name, search_keywords)
                    VALUES (:brand, :model, :socket, :chipset, :form_factor, :ram_slots,
                            :normalized_name, :search_keywords)
                """),
                {
                    "brand": mb["brand"],
                    "model": mb["model"],
                    "socket": mb["socket"],
                    "chipset": mb["chipset"],
                    "form_factor": mb["form_factor"],
                    "ram_slots": mb["ram_slots"],
                    "normalized_name": normalize_text(f"{mb['brand']} {mb['model']}"),
                    "search_keywords": keywords
                }
            )
            added += 1
            print(f"  [OK] Added {mb['brand']} {mb['model']}")
        
        session.commit()
        print(f"\nTotal added: {added} motherboards")


if __name__ == "__main__":
    add_msi_mag_motherboard()
