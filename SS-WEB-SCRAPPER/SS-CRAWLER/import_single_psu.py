#!/usr/bin/env python3
"""Import a single new PSU entry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def import_single_psu():
    """Import Energon Eps-650W PSU."""
    print("Importing Energon Eps-650W...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Check if already exists
        result = session.execute(
            text("SELECT psu_id FROM psu_reference WHERE name = :name"),
            {"name": "Energon Eps-650W"}
        ).fetchone()
        
        if result:
            print(f"Already exists with ID: {result[0]}")
            return
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(psu_id), 0) FROM psu_reference")).scalar()
        new_id = max_id + 1
        
        # Insert new PSU
        session.execute(
            text("""
                INSERT INTO psu_reference 
                (psu_id, name, form_factor, efficiency_rating, wattage, modular, rating, price, search_keywords)
                VALUES (:id, :name, :form, :efficiency, :wattage, :modular, :rating, :price, :keywords)
            """),
            {
                "id": new_id,
                "name": "Energon Eps-650W",
                "form": "ATX",
                "efficiency": "80+",
                "wattage": "650",
                "modular": None,
                "rating": None,
                "price": None,
                "keywords": ["energon", "eps650w", "energon eps 650w"]
            }
        )
        session.commit()
        print(f"✅ Imported: Energon Eps-650W (ID: {new_id})")

if __name__ == "__main__":
    import_single_psu()
