#!/usr/bin/env python3
"""Import RAM reference data from ram.csv into the database."""
import sys
import csv
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_database, get_session
from src.utils.text import normalize_text
from sqlalchemy import text

def extract_capacity_gb(name: str) -> int:
    """Extract capacity in GB from RAM name."""
    match = re.search(r'(\d+)\s*GB', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def generate_keywords(name: str, speed: str) -> list:
    """Generate search keywords for RAM."""
    keywords = [
        normalize_text(re.sub(r'[^a-zA-Z0-9]', '', name)),  # alphanumeric only
        normalize_text(name),
        normalize_text(re.sub(r'[^a-zA-Z0-9]', ' ', name)),  # spaced version
        normalize_text(speed)
    ]
    return list(set([k for k in keywords if k]))

def import_ram():
    """Import RAM data from ram.csv."""
    print("Importing RAM reference data...")
    
    # Initialize database
    from src.utils.config import AppConfig
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    csv_path = Path(__file__).parent / "ram.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found!")
        return
    
    imported = 0
    
    with get_session() as session:
        # Check if table has data
        result = session.execute(text("SELECT COUNT(*) FROM ram_reference")).scalar()
        if result > 0:
            print(f"RAM reference table already has {result} entries. Skipping import.")
            return
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row['Name'].strip()
                speed = row['Speed'].strip()
                modules = row['Modules'].strip() if row['Modules'] else None
                
                # Parse numeric fields
                first_word_latency = None
                if row['First Word Latency'] and row['First Word Latency'].strip():
                    try:
                        first_word_latency = float(row['First Word Latency'])
                    except ValueError:
                        pass
                
                cas_latency = None
                if row['CAS Latency'] and row['CAS Latency'].strip():
                    try:
                        cas_latency = int(row['CAS Latency'])
                    except ValueError:
                        pass
                
                rating = None
                if row['Rating'] and row['Rating'].strip():
                    try:
                        rating = int(row['Rating'])
                    except ValueError:
                        pass
                
                price = None
                if row['Price'] and row['Price'].strip():
                    try:
                        price = float(row['Price'])
                    except ValueError:
                        pass
                
                capacity_gb = extract_capacity_gb(name)
                search_keywords = generate_keywords(name, speed)
                normalized_name = normalize_text(re.sub(r'[^a-zA-Z0-9]', '', name))
                
                session.execute(
                    text("""
                        INSERT INTO ram_reference 
                        (name, speed, modules, first_word_latency, cas_latency, 
                         rating, price, capacity_gb, search_keywords, normalized_name)
                        VALUES 
                        (:name, :speed, :modules, :first_word_latency, :cas_latency,
                         :rating, :price, :capacity_gb, :search_keywords, :normalized_name)
                    """),
                    {
                        "name": name,
                        "speed": speed,
                        "modules": modules,
                        "first_word_latency": first_word_latency,
                        "cas_latency": cas_latency,
                        "rating": rating,
                        "price": price,
                        "capacity_gb": capacity_gb,
                        "search_keywords": search_keywords,
                        "normalized_name": normalized_name
                    }
                )
                imported += 1
        
        session.commit()
    
    print(f"Successfully imported {imported} RAM models into ram_reference table")

if __name__ == "__main__":
    import_ram()
