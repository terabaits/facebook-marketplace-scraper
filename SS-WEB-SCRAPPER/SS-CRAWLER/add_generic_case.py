#!/usr/bin/env python3
"""Add a generic PC case entry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def add_generic_case():
    """Add a generic ATX case entry."""
    print("Adding generic PC case...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Check if already exists
        result = session.execute(
            text("SELECT id FROM case_reference WHERE name = :name"),
            {"name": "Generic ATX Case"}
        ).fetchone()
        
        if result:
            print(f"Generic case already exists with ID: {result[0]}")
            return result[0]
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM case_reference")).scalar()
        new_id = max_id + 1
        
        # Generate search keywords
        name = "Generic ATX Case"
        keywords = [
            normalize_text(name),
            "generic",
            "case",
            "atx",
            "pc case",
            "computer case",
            "tower",
        ]
        
        # Insert new case
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
                "side_panel": None,
                "external_volume": None,
                "internal_35_bays": 2,
                "rating": None,
                "price": 15.00,
                "search_keywords": keywords,
                "normalized_name": normalize_text(name)
            }
        )
        session.commit()
        print(f"[OK] Added generic case: {name} (ID: {new_id})")
        return new_id


if __name__ == "__main__":
    add_generic_case()
