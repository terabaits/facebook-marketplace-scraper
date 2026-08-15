#!/usr/bin/env python3
"""Import Case reference data from cases.csv into the database."""
import sys
import csv
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.text import normalize_text
from sqlalchemy import text


def import_cases():
    """Import Case data from cases.csv."""
    print("Importing Case reference data...")
    
    # Change to script directory to find config.yaml
    import os
    os.chdir(Path(__file__).parent)
    
    from src.utils.config import AppConfig
    config = AppConfig.from_yaml("config.yaml")
    init_database(config.database)
    
    csv_path = Path(__file__).parent / "cases.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        return
    
    imported = 0
    
    with get_session() as session:
        result = session.execute(text("SELECT COUNT(*) FROM case_reference")).scalar()
        if result > 0:
            print(f"Case reference table already has {result} entries. Skipping import.")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row['Name'].strip()
                
                # Generate search keywords
                keywords = [
                    normalize_text(re.sub(r'[^a-zA-Z0-9]', '', name)),
                    normalize_text(name),
                    normalize_text(re.sub(r'[^a-zA-Z0-9]', ' ', name)),
                ]
                keywords = list(set([k for k in keywords if k]))
                
                session.execute(
                    text("""
                        INSERT INTO case_reference 
                        (name, type, color, power_supply, side_panel, external_volume, 
                         internal_35_bays, rating, price, search_keywords, normalized_name)
                        VALUES (:name, :type, :color, :power_supply, :side_panel, 
                                :external_volume, :internal_35_bays, :rating, :price, 
                                :search_keywords, :normalized_name)
                    """),
                    {
                        "name": name,
                        "type": row.get('Type', ''),
                        "color": row.get('Color', ''),
                        "power_supply": row.get('Power Supply', ''),
                        "side_panel": row.get('Side Panel', ''),
                        "external_volume": row.get('External volume', ''),
                        "internal_35_bays": row.get('Internal 3.5" bays', ''),
                        "rating": row.get('Rating', ''),
                        "price": row.get('Price', ''),
                        "search_keywords": keywords,
                        "normalized_name": normalize_text(name)
                    }
                )
                imported += 1
                
                if imported % 100 == 0:
                    print(f"  Imported {imported} cases...")
        
        session.commit()
    
    print(f"Imported {imported} case references")


if __name__ == "__main__":
    import_cases()
