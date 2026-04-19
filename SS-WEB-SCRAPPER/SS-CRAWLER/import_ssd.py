"""Import SSD.csv into the database using psycopg2 directly."""
import csv
import sys
import re
from pathlib import Path
import psycopg2

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def normalize_text(text):
    """Normalize text for matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_capacity(capacity_str):
    """Parse capacity string and return GB."""
    if not capacity_str:
        return None
    
    capacity_str = capacity_str.strip().upper()
    match = re.search(r'(\d+)', capacity_str)
    if not match:
        return None
    
    val = int(match.group(1))
    
    if 'TB' in capacity_str:
        val = val * 1000
    
    return val


def parse_boolean(val):
    """Parse Yes/No to boolean."""
    if not val:
        return None
    return val.strip().lower() == 'yes'


def generate_search_keywords(brand, model):
    """Generate search keywords for an SSD."""
    keywords = []
    
    brand_lower = brand.lower()
    keywords.append(brand_lower)
    
    model_lower = model.lower()
    keywords.append(model_lower)
    
    keywords.append(f"{brand_lower} {model_lower}")
    
    numbers = re.findall(r'\d+', model)
    for num in numbers:
        keywords.append(num)
        keywords.append(f"{brand_lower} {num}")
    
    clean_model = re.sub(r'[^\w\s]', ' ', model_lower)
    clean_model = re.sub(r'\s+', ' ', clean_model).strip()
    keywords.append(clean_model)
    
    return list(set(keywords))


def import_ssd_csv(csv_path):
    """Import SSD.csv into the database."""
    print(f"Importing SSDs from {csv_path}")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    count = 0
    errors = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                brand = row.get('Brand', '').strip()
                model = row.get('Model', '').strip()
                
                if not brand or not model:
                    continue
                
                capacity = parse_capacity(row.get('Capacities', ''))
                
                read_speed = None
                write_speed = None
                try:
                    read_speed = int(row.get('R (Up to, in MB/s)', ''))
                except (ValueError, TypeError):
                    pass
                try:
                    write_speed = int(row.get('W (Up to, in MB/s)', ''))
                except (ValueError, TypeError):
                    pass
                
                keywords = generate_search_keywords(brand, model)
                normalized = normalize_text(f"{brand} {model}")
                
                cursor.execute("""
                    INSERT INTO ssd_reference (
                        brand, model, interface, form_factor, capacity_gb,
                        controller, configuration, has_dram, hmb,
                        nand_brand, nand_type, layers,
                        read_speed_mb, write_speed_mb,
                        category, notes,
                        search_keywords, normalized_name
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s
                    )
                    ON CONFLICT DO NOTHING
                """, (
                    brand,
                    model,
                    row.get('Interface', '').strip() or None,
                    row.get('Form Factor', '').strip() or None,
                    capacity,
                    row.get('Controller', '').strip() or None,
                    row.get('Configuration', '').strip() or None,
                    parse_boolean(row.get('DRAM', '')),
                    row.get('HMB', '').strip() if row.get('HMB', '').strip() != 'N/A' else None,
                    row.get('NAND Brand', '').strip() or None,
                    row.get('NAND Type', '').strip() or None,
                    row.get('Layers', '').strip() or None,
                    read_speed,
                    write_speed,
                    row.get('Categories', '').strip() or None,
                    row.get('Notes (*)', '').strip() or None,
                    keywords,
                    normalized
                ))
                
                count += 1
                if count % 100 == 0:
                    print(f"  Imported {count} SSDs...")
                    
            except Exception as e:
                print(f"  Error importing row: {e}")
                errors += 1
        
        conn.commit()
    
    cursor.close()
    conn.close()
    
    print(f"\nImport complete!")
    print(f"  Total imported: {count}")
    print(f"  Errors: {errors}")


if __name__ == '__main__':
    csv_path = Path(__file__).parent / 'SSD.csv'
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)
    
    import_ssd_csv(csv_path)
