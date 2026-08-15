#!/usr/bin/env python3
"""Import new PSU entries from psu.csv that don't exist in the database."""
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text

def import_new_psus():
    """Import only new PSU entries from psu.csv."""
    print("Checking for new PSU entries...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    csv_path = Path(__file__).parent / "psu.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        return
    
    with get_session() as session:
        # Get existing PSU names
        existing = set()
        result = session.execute(text("SELECT name FROM psu_reference"))
        for row in result:
            existing.add(row[0])
        
        print(f"Database has {len(existing)} PSUs")
        
        # Read CSV and find new entries
        new_entries = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Name'].strip()
                if name not in existing:
                    new_entries.append(row)
        
        if not new_entries:
            print("No new entries to import.")
            return
        
        print(f"Found {len(new_entries)} new entries to import")
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(psu_id), 0) FROM psu_reference")).scalar()
        
        # Import new entries
        imported = 0
        for row in new_entries:
            max_id += 1
            name = row['Name'].strip()
            
            # Generate search keywords
            keywords = [
                normalize_text(name),
                normalize_text(name.replace(' ', '')),
                normalize_text(name.replace('-', ' ')),
            ]
            keywords = list(set([k for k in keywords if k]))
            
            # Parse wattage - remove 'W' and spaces
            wattage = row.get('Wattage', '').strip()
            if wattage:
                wattage = wattage.replace('W', '').replace('w', '').strip()
            
            session.execute(
                text("""
                    INSERT INTO psu_reference 
                    (psu_id, name, form_factor, efficiency_rating, wattage, modular, rating, price, search_keywords)
                    VALUES (:id, :name, :form, :efficiency, :wattage, :modular, :rating, :price, :keywords)
                """),
                {
                    "id": max_id,
                    "name": name,
                    "form": row.get('Form Factor'),
                    "efficiency": row.get('Efficiency Rating'),
                    "wattage": wattage if wattage else None,
                    "modular": row.get('Modular'),
                    "rating": int(row['Rating']) if row.get('Rating') and row['Rating'].strip() else None,
                    "price": float(row['Price']) if row.get('Price') and row['Price'].strip() else None,
                    "keywords": keywords
                }
            )
            imported += 1
            print(f"  + {name}")
        
        session.commit()
        print(f"\n✅ Imported {imported} new PSU(s)")

if __name__ == "__main__":
    import_new_psus()
