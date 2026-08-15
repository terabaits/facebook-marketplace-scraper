#!/usr/bin/env python3
"""Import motherboard and monitor reference data from Excel files."""
import sys
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import text, create_engine

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def get_connection_string():
    """Create PostgreSQL connection string."""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def normalize_text(text):
    """Normalize text for search matching."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_search_keywords(brand, model, chipset, socket):
    """Generate search keywords for a motherboard."""
    keywords = set()
    
    if brand:
        keywords.add(brand.lower())
        # Add brand variations
        if 'asrock' in brand.lower():
            keywords.add('as rock')
        elif 'msi' in brand.lower():
            keywords.add('microstar')
    
    if model:
        # Add full model
        keywords.add(model.lower())
        # Add model without spaces
        keywords.add(model.lower().replace(' ', ''))
        # Add model number parts
        parts = model.split()
        for part in parts:
            if len(part) >= 2:
                keywords.add(part.lower())
    
    if chipset:
        keywords.add(chipset.lower())
    
    if socket:
        keywords.add(socket.lower())
    
    return list(keywords)


def generate_monitor_keywords(brand, model, size, resolution):
    """Generate search keywords for a monitor."""
    keywords = set()
    
    if brand:
        keywords.add(brand.lower())
    
    if model:
        keywords.add(model.lower())
        keywords.add(model.lower().replace(' ', ''))
    
    if size:
        keywords.add(f"{size}")
        keywords.add(f"{size}inch")
        keywords.add(f"{size}\"")
    
    if resolution:
        res_lower = resolution.lower()
        keywords.add(res_lower)
        if '1080' in res_lower:
            keywords.add('fullhd')
            keywords.add('fhd')
        elif '1440' in res_lower:
            keywords.add('qhd')
            keywords.add('wqhd')
        elif '2160' in res_lower or '4k' in res_lower:
            keywords.add('4k')
            keywords.add('uhd')
    
    return list(keywords)


def import_motherboards(engine):
    """Import motherboard data from Excel file."""
    print("Importing motherboard data...")
    
    df = pd.read_excel('Motherboards.xlsx')
    
    # Clean column names
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    
    print(f"Found {len(df)} motherboards in Excel file")
    
    records = []
    for idx, row in df.iterrows():
        try:
            brand = str(row.get('Brand', '')).strip() if pd.notna(row.get('Brand')) else None
            model = str(row.get('Model', '')).strip() if pd.notna(row.get('Model')) else None
            socket = str(row.get('Socket', '')).strip() if pd.notna(row.get('Socket')) else None
            chipset = str(row.get('Chipset', '')).strip() if pd.notna(row.get('Chipset')) else None
            ram_slots = str(row.get('RAM slots', '')).strip() if pd.notna(row.get('RAM slots')) else None
            form_factor = str(row.get('Form Factor', '')).strip() if pd.notna(row.get('Form Factor')) else None
            
            if not brand or not model:
                print(f"Skipping row {idx}: missing brand or model")
                continue
            
            # Normalize
            normalized_name = normalize_text(f"{brand} {model}")
            
            # Generate search keywords
            search_keywords = generate_search_keywords(brand, model, chipset, socket)
            
            records.append({
                'brand': brand,
                'model': model,
                'socket': socket,
                'chipset': chipset,
                'ram_slots': ram_slots,
                'form_factor': form_factor,
                'normalized_name': normalized_name,
                'search_keywords': search_keywords
            })
            
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            continue
    
    # Clear existing data with CASCADE to handle foreign key constraints
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE motherboard_models CASCADE"))
        conn.commit()
    
    # Insert new data
    with engine.connect() as conn:
        for record in records:
            conn.execute(text("""
                INSERT INTO motherboard_models 
                (brand, model, socket, chipset, ram_slots, form_factor, normalized_name, search_keywords)
                VALUES (:brand, :model, :socket, :chipset, :ram_slots, :form_factor, :normalized_name, :search_keywords)
            """), record)
        conn.commit()
    
    print(f"Successfully imported {len(records)} motherboards")


def import_monitors(engine):
    """Import monitor data from Excel file."""
    print("Importing monitor data...")
    
    df = pd.read_excel('monitors.xlsx')
    
    # Clean column names
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    
    print(f"Found {len(df)} monitors in Excel file")
    print(f"Columns: {df.columns.tolist()}")
    
    # Check first few rows to understand structure
    print("\nSample data:")
    print(df.head(3).to_string())
    
    records = []
    for idx, row in df.iterrows():
        try:
            # Try different column name variations
            brand = None
            model = None
            size = None
            resolution = None
            refresh_rate = None
            panel_type = None
            
            # Check for common column names
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'product_name':
                    product_name = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
                elif col_lower == 'manufacturer':
                    manufacturer = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
                elif 'size' in col_lower or 'screen' in col_lower or col_lower == 'screen_size':
                    size = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
                elif col_lower == 'resolution':
                    resolution = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
                elif 'refresh' in col_lower:
                    refresh_rate = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
                elif col_lower == 'panel_type':
                    panel_type = str(row.get(col, '')).strip() if pd.notna(row.get(col)) else None
            
            # Parse product_name to extract brand and model
            if product_name:
                # Try to extract manufacturer from product_name if manufacturer column is empty
                if not manufacturer:
                    # Common patterns: "Brand Model Name" or "Brand ModelName"
                    parts = product_name.split(maxsplit=1)
                    if parts:
                        manufacturer = parts[0]
                
                # Extract model from product_name
                if manufacturer and product_name.lower().startswith(manufacturer.lower()):
                    model = product_name[len(manufacturer):].strip()
                else:
                    # Try manufacturer column
                    if manufacturer:
                        # product_name might contain manufacturer, extract model
                        if manufacturer.lower() in product_name.lower():
                            model = product_name.replace(manufacturer, '').strip()
                        else:
                            # manufacturer is separate, model is rest of product_name
                            parts = product_name.split(maxsplit=1)
                            if len(parts) > 1:
                                model = parts[1]
                            else:
                                model = product_name
                    else:
                        parts = product_name.split(maxsplit=1)
                        manufacturer = parts[0] if parts else None
                        model = parts[1] if len(parts) > 1 else product_name
            
            brand = manufacturer
            
            if not brand or not model:
                print(f"Skipping row {idx}: missing brand or model (brand={brand}, model={model})")
                continue
            
            # Clean size - extract number
            if size:
                size_match = re.search(r'(\d+(?:\.\d+)?)', str(size))
                if size_match:
                    size = size_match.group(1)
            
            # Clean refresh rate - extract number
            if refresh_rate:
                refresh_match = re.search(r'(\d+)', str(refresh_rate))
                if refresh_match:
                    refresh_rate = refresh_match.group(1)
            
            # Normalize
            normalized_name = normalize_text(f"{brand} {model}")
            
            # Generate search keywords
            search_keywords = generate_monitor_keywords(brand, model, size, resolution)
            
            records.append({
                'brand': brand,
                'model': model,
                'size': size,
                'resolution': resolution,
                'refresh_rate': refresh_rate,
                'panel_type': panel_type,
                'normalized_name': normalized_name,
                'search_keywords': search_keywords
            })
            
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Clear existing data with CASCADE to handle foreign key constraints
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE monitor_models CASCADE"))
        conn.commit()
    
    # Insert new data
    with engine.connect() as conn:
        for record in records:
            conn.execute(text("""
                INSERT INTO monitor_models 
                (brand, model, size, resolution, refresh_rate, panel_type, normalized_name, search_keywords)
                VALUES (:brand, :model, :size, :resolution, :refresh_rate, :panel_type, :normalized_name, :search_keywords)
            """), record)
        conn.commit()
    
    print(f"Successfully imported {len(records)} monitors")


def main():
    """Main entry point."""
    engine = create_engine(get_connection_string())
    
    print("=" * 60)
    print("Motherboard and Monitor Import Tool")
    print("=" * 60)
    
    # Import motherboards
    if Path('Motherboards.xlsx').exists():
        import_motherboards(engine)
    else:
        print("Motherboards.xlsx not found, skipping...")
    
    print()
    
    # Import monitors
    if Path('monitors.xlsx').exists():
        import_monitors(engine)
    else:
        print("monitors.xlsx not found, skipping...")
    
    print()
    print("=" * 60)
    print("Import complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
