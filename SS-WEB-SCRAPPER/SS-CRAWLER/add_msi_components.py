#!/usr/bin/env python3
"""Add MSI MAG components to database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text
import re


def add_msi_mag_psus():
    """Add MSI MAG PSU entries if missing."""
    print("Checking for MSI MAG PSUs...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Check which MSI MAG PSUs exist
        target_ids = [7497, 7498, 7505]
        existing = session.execute(
            text("SELECT id, name FROM psu_reference WHERE id IN :ids"),
            {"ids": tuple(target_ids)}
        ).fetchall()
        
        print(f"Found {len(existing)} existing MSI MAG PSUs:")
        for row in existing:
            print(f"  ID {row[0]}: {row[1]}")
        
        existing_ids = {row[0] for row in existing}
        
        # Add missing ones
        psus_to_add = [
            {"id": 7497, "name": "MSI MAG A650BN", "wattage": 650},
            {"id": 7498, "name": "MSI MAG A650GF", "wattage": 650},
            {"id": 7505, "name": "MSI MAG A750GF", "wattage": 750},
        ]
        
        added = 0
        for psu in psus_to_add:
            if psu["id"] not in existing_ids:
                keywords = [
                    normalize_text(psu["name"]),
                    "msi", "mag", "msi mag",
                    psu["name"].lower().replace(" ", ""),
                ]
                
                session.execute(
                    text("""
                        INSERT INTO psu_reference 
                        (id, name, wattage, search_keywords, normalized_name)
                        VALUES (:id, :name, :wattage, :keywords, :normalized)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            wattage = EXCLUDED.wattage,
                            search_keywords = EXCLUDED.search_keywords,
                            normalized_name = EXCLUDED.normalized_name
                    """),
                    {
                        "id": psu["id"],
                        "name": psu["name"],
                        "wattage": psu["wattage"],
                        "keywords": keywords,
                        "normalized": normalize_text(psu["name"])
                    }
                )
                added += 1
                print(f"  [OK] Added {psu['name']} (ID: {psu['id']})")
        
        if added == 0:
            print("  All MSI MAG PSUs already exist")
        
        session.commit()


def add_msi_mag_case():
    """Add MSI MAG 100R case."""
    print("\nChecking for MSI MAG 100R case...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Check if exists
        result = session.execute(
            text("SELECT id FROM case_reference WHERE name ILIKE :name"),
            {"name": "%msi mag 100r%"}
        ).fetchone()
        
        if result:
            print(f"  MSI MAG 100R already exists (ID: {result[0]})")
            return result[0]
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM case_reference")).scalar()
        new_id = max_id + 1
        
        name = "MSI MAG Forge 100R"
        keywords = [
            normalize_text(name),
            "msi", "mag", "forge", "100r",
            "msi mag", "mag forge", "msi 100r",
        ]
        
        session.execute(
            text("""
                INSERT INTO case_reference 
                (id, name, type, color, power_supply, side_panel, external_volume,
                 internal_35_bays, rating, price, search_keywords, normalized_name)
                VALUES (:id, :name, :type, :color, :power_supply, :side_panel, 
                        :external_volume, :internal_35_bays, :rating, :price, 
                        :search_keywords, :normalized_name)
            """),
            {
                "id": new_id,
                "name": name,
                "type": "ATX Mid Tower",
                "color": "Black",
                "power_supply": "None",
                "side_panel": "Tempered Glass",
                "external_volume": 45.0,
                "internal_35_bays": 2,
                "rating": None,
                "price": 65.0,
                "search_keywords": keywords,
                "normalized_name": normalize_text(name)
            }
        )
        session.commit()
        print(f"  [OK] Added {name} (ID: {new_id})")
        return new_id


if __name__ == "__main__":
    add_msi_mag_psus()
    add_msi_mag_case()
    print("\nDone!")
