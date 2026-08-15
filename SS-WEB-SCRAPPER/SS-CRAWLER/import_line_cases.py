#!/usr/bin/env python3
"""Import a specific line from cases.csv by line number."""
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def import_line(line_number: int):
    """Import a specific line from cases.csv."""
    print(f"Importing line {line_number} from cases.csv...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    csv_path = Path(__file__).parent / "cases.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        return
    
    # Read specific line (1-indexed, line 1 is header)
    target_row = None
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # Start at 2 (line 1 is header)
            if i == line_number:
                target_row = row
                break
    
    if not target_row:
        print(f"Error: Line {line_number} not found in cases.csv")
        return
    
    name = target_row['Name'].strip()
    print(f"Found: {name}")
    
    with get_session() as session:
        # Check if already exists
        result = session.execute(
            text("SELECT id FROM case_reference WHERE name = :name"),
            {"name": name}
        ).fetchone()
        
        if result:
            print(f"Already exists with ID: {result[0]}")
            return
        
        # Get max ID
        max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM case_reference")).scalar()
        new_id = max_id + 1
        
        # Generate search keywords
        keywords = [
            normalize_text(name),
            normalize_text(name.replace(' ', '')),
            normalize_text(name.replace('-', ' ')),
        ]
        keywords = list(set([k for k in keywords if k]))
        
        session.execute(
            text("""
                INSERT INTO case_reference 
                (id, name, normalized_name, case_type, color, power_supply, side_panel, 
                 external_volume, internal_35_bays, rating, price, search_keywords)
                VALUES (:id, :name, :normalized_name, :case_type, :color, :power_supply, 
                        :side_panel, :external_volume, :internal_35_bays, :rating, :price, :keywords)
            """),
            {
                "id": new_id,
                "name": name,
                "normalized_name": normalize_text(name),
                "case_type": target_row.get('Type'),
                "color": target_row.get('Color'),
                "power_supply": target_row.get('Power Supply') if target_row.get('Power Supply') else None,
                "side_panel": target_row.get('Side Panel') if target_row.get('Side Panel') else None,
                "external_volume": float(target_row['External volume']) if target_row.get('External volume') and target_row['External volume'].strip() else None,
                "internal_35_bays": int(target_row['Internal 3.5" bays']) if target_row.get('Internal 3.5" bays') and target_row['Internal 3.5" bays'].strip() else None,
                "rating": int(target_row['Rating']) if target_row.get('Rating') and target_row['Rating'].strip() else None,
                "price": float(target_row['Price']) if target_row.get('Price') and target_row['Price'].strip() else None,
                "keywords": keywords
            }
        )
        session.commit()
        print(f"✅ Imported: {name} (ID: {new_id})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_line_cases.py <line_number>")
        print("Example: python import_line_cases.py 5738")
        sys.exit(1)
    
    try:
        line_num = int(sys.argv[1])
        import_line(line_num)
    except ValueError:
        print("Error: Line number must be an integer")
        sys.exit(1)
