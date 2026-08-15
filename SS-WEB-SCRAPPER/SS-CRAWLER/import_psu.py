#!/usr/bin/env python3
"""Import PSU reference data from psu.csv into the database."""
import sys
import csv
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.text import normalize_text
from sqlalchemy import text


def import_psu():
    """Import PSU data from psu.csv."""
    print("Importing PSU reference data...")
    
    from src.utils.config import AppConfig
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    csv_path = Path(__file__).parent / "psu.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        return
    
    imported = 0
    
    with get_session() as session:
        result = session.execute(text("SELECT COUNT(*) FROM psu_reference")).scalar()
        if result > 0:
            print(f"PSU reference table already has {result} entries. Skipping import.")
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
                
                # Extract wattage as integer
                wattage_str = row.get('Wattage', '')
                wattage = None
                match = re.search(r'(\d+)', wattage_str)
                if match:
                    wattage = int(match.group(1))
                
                session.execute(
                    text("""
                        INSERT INTO psu_reference 
                        (name, form_factor, efficiency_rating, wattage, modular, 
                         rating, price, search_keywords, normalized_name)
                        VALUES (:name, :form_factor, :efficiency_rating, :wattage, 
                                :modular, :rating, :price, :search_keywords, :normalized_name)
                    """),
                    {
                        "name": name,
                        "form_factor": row.get('Form Factor', ''),
                        "efficiency_rating": row.get('Efficiency Rating', ''),
                        "wattage": wattage,
                        "modular": row.get('Modular', ''),
                        "rating": row.get('Rating', ''),
                        "price": row.get('Price', ''),
                        "search_keywords": keywords,
                        "normalized_name": normalize_text(name)
                    }
                )
                imported += 1
                
                if imported % 100 == 0:
                    print(f"  Imported {imported} PSUs...")
        
        session.commit()
    
    print(f"Imported {imported} PSU references")


if __name__ == "__main__":
    import_psu()
