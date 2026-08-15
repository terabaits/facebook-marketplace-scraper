#!/usr/bin/env python3
"""Import a specific line from CSV files (PSU or Cases) by line number."""
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text


def import_psu_line(csv_path: Path, line_number: int, session):
    """Import a specific line from psu.csv."""
    target_row = None
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            if i == line_number:
                target_row = row
                break
    
    if not target_row:
        print(f"Error: Line {line_number} not found in psu.csv")
        return False
    
    name = target_row['Name'].strip()
    print(f"Found PSU: {name}")
    
    # Check if already exists
    result = session.execute(
        text("SELECT id FROM psu_reference WHERE name = :name"),
        {"name": name}
    ).fetchone()
    
    if result:
        print(f"Already exists with ID: {result[0]}")
        return False
    
    # Parse wattage
    wattage = target_row.get('Wattage', '').strip()
    if wattage:
        wattage = wattage.replace('W', '').replace('w', '').strip()
    
    # Generate search keywords
    keywords = [
        normalize_text(name),
        normalize_text(name.replace(' ', '')),
        normalize_text(name.replace('-', ' ')),
    ]
    keywords = list(set([k for k in keywords if k]))
    
    session.execute(
        text("""
            INSERT INTO psu_reference 
            (name, normalized_name, form_factor, efficiency_rating, wattage, modular, rating, price, search_keywords)
            VALUES (:name, :normalized_name, :form, :efficiency, :wattage, :modular, :rating, :price, :keywords)
        """),
        {
            "name": name,
            "normalized_name": normalize_text(name),
            "form": target_row.get('Form Factor'),
            "efficiency": target_row.get('Efficiency Rating'),
            "wattage": wattage if wattage else None,
            "modular": target_row.get('Modular') if target_row.get('Modular') else None,
            "rating": int(target_row['Rating']) if target_row.get('Rating') and target_row['Rating'].strip() else None,
            "price": float(target_row['Price']) if target_row.get('Price') and target_row['Price'].strip() else None,
            "keywords": keywords
        }
    )
    session.commit()
    print(f"✅ Imported PSU: {name}")
    return True


def import_case_line(csv_path: Path, line_number: int, session):
    """Import a specific line from cases.csv."""
    target_row = None
    
    # Try different encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=2):
                    if i == line_number:
                        target_row = row
                        break
            if target_row:
                break
        except UnicodeDecodeError:
            continue
    
    if not target_row:
        print(f"Error: Line {line_number} not found in cases.csv or encoding issues")
        return False
    
    name = target_row['Name'].strip()
    print(f"Found Case: {name}")
    
    # Check if already exists
    result = session.execute(
        text("SELECT id FROM case_reference WHERE name = :name"),
        {"name": name}
    ).fetchone()
    
    if result:
        print(f"Already exists with ID: {result[0]}")
        return False
    
    # Generate search keywords
    keywords = [
        normalize_text(name),
        normalize_text(name.replace(' ', '')),
        normalize_text(name.replace('-', ' ')),
    ]
    keywords = list(set([k for k in keywords if k]))
    
    # Parse values
    rating = target_row.get('Rating')
    rating_int = int(rating) if rating and rating.strip() and rating.isdigit() else None
    
    price = target_row.get('Price')
    price_float = float(price) if price and price.strip() else None
    
    session.execute(
        text("""
            INSERT INTO case_reference 
            (name, normalized_name, type, color, power_supply, side_panel, 
             external_volume, internal_35_bays, rating, price, search_keywords)
            VALUES (:name, :normalized_name, :type, :color, :power_supply, 
                    :side_panel, :external_volume, :internal_35_bays, :rating, :price, :keywords)
        """),
        {
            "name": name,
            "normalized_name": normalize_text(name),
            "type": target_row.get('Type') or None,
            "color": target_row.get('Color') or None,
            "power_supply": target_row.get('Power Supply') or None,
            "side_panel": target_row.get('Side Panel') or None,
            "external_volume": target_row.get('External volume') or None,
            "internal_35_bays": target_row.get('Internal 3.5" bays') or None,
            "rating": rating_int,
            "price": price_float,
            "keywords": keywords
        }
    )
    session.commit()
    print(f"✅ Imported Case: {name}")
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python import_line.py <table> <line_number>")
        print("  table: 'psu' or 'case'")
        print("Examples:")
        print("  python import_line.py psu 2896")
        print("  python import_line.py case 5738")
        sys.exit(1)
    
    table = sys.argv[1].lower()
    try:
        line_num = int(sys.argv[2])
    except ValueError:
        print("Error: Line number must be an integer")
        sys.exit(1)
    
    if table not in ['psu', 'case']:
        print(f"Error: Unknown table '{table}'. Use 'psu' or 'case'.")
        sys.exit(1)
    
    # Setup database
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    # Determine CSV file
    csv_filename = 'psu.csv' if table == 'psu' else 'cases.csv'
    csv_path = Path(__file__).parent / csv_filename
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        sys.exit(1)
    
    # Import
    with get_session() as session:
        if table == 'psu':
            import_psu_line(csv_path, line_num, session)
        else:
            import_case_line(csv_path, line_num, session)


if __name__ == "__main__":
    main()
