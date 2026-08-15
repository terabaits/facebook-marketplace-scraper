#!/usr/bin/env python3
"""Import console reference data from CSV files."""
import csv
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

# Database connection - adjust these
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "ss_market"
DB_USER = "crawler"
DB_PASS = "crawler_pass"

CONSOLES_DIR = Path("G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/Consoles")

def normalize_name(name: str) -> str:
    """Normalize name for matching."""
    return re.sub(r'[^\w\s]', '', name.lower()).strip()

def extract_keywords(name: str) -> List[str]:
    """Extract search keywords from name."""
    keywords = []
    name_lower = name.lower()
    
    # Common patterns
    if 'playstation' in name_lower or 'ps' in name_lower:
        keywords.extend(['playstation', 'ps'])
        if 'ps5' in name_lower or 'playstation 5' in name_lower:
            keywords.extend(['ps5', 'playstation 5'])
        if 'ps4' in name_lower or 'playstation 4' in name_lower:
            keywords.extend(['ps4', 'playstation 4'])
        if 'ps3' in name_lower or 'playstation 3' in name_lower:
            keywords.extend(['ps3', 'playstation 3'])
    
    if 'xbox' in name_lower:
        keywords.append('xbox')
        if 'series x' in name_lower:
            keywords.extend(['series x', 'xbox x'])
        if 'series s' in name_lower:
            keywords.extend(['series s', 'xbox s'])
        if 'one' in name_lower:
            keywords.append('xbox one')
        if '360' in name_lower:
            keywords.append('xbox 360')
    
    if 'switch' in name_lower or 'nintendo' in name_lower:
        keywords.extend(['switch', 'nintendo', 'nintendo switch'])
        if 'oled' in name_lower:
            keywords.extend(['oled', 'switch oled'])
        if 'lite' in name_lower:
            keywords.extend(['lite', 'switch lite'])
    
    return list(set(keywords))

def import_consoles(cur):
    """Import main console list."""
    csv_file = CONSOLES_DIR / "console_list.csv"
    if not csv_file.exists():
        print(f"Warning: {csv_file} not found")
        return
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('System Name', '').strip()
            if not name:
                continue
            
            company = row.get('Company', '').strip()[:50] or None
            release = row.get('Release', '').strip()[:50] or None
            
            # Extract generation
            gen_str = row.get('GEN', '')
            generation = int(gen_str) if gen_str and gen_str.isdigit() else None
            
            keywords = extract_keywords(name)
            normalized = normalize_name(name)
            
            # Insert console
            cur.execute("""
                INSERT INTO console_reference (name, company, generation, release_date, search_keywords, normalized_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (name[:100], company, generation, release, keywords, normalized[:200]))
    
    print("Imported consoles from console_list.csv")

def import_variants(cur, console_name: str, csv_file: Path):
    """Import variants for a specific console."""
    if not csv_file.exists():
        return 0
    
    # Get console ID
    cur.execute("""
        SELECT id FROM console_reference 
        WHERE name ILIKE %s OR normalized_name ILIKE %s
    """, (f'%{console_name}%', f'%{console_name}%'))
    
    console_row = cur.fetchone()
    if not console_row:
        print(f"  Console '{console_name}' not found in database, skipping {csv_file.name}")
        return 0
    
    console_id = console_row[0]
    count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle different CSV formats
            model = row.get('Model', row.get('model', '')).strip()
            sku = row.get('SKU', row.get('sku', '')).strip()
            storage_str = row.get('Storage', row.get('storage', row.get('HDD', ''))).strip()
            region = row.get('Region', row.get('region', '')).strip()
            release = row.get('Release Date', row.get('release_date', '')).strip()
            
            # Parse storage
            storage_gb = None
            if storage_str:
                match = re.search(r'(\d+)\s*(GB|TB)', storage_str.upper())
                if match:
                    size = int(match.group(1))
                    unit = match.group(2)
                    storage_gb = size * 1024 if unit == 'TB' else size
            
            # Build model name
            if not model:
                # Try to construct from other fields
                version = row.get('Version', '').strip()
                type_field = row.get('Type', '').strip()
                if version and type_field:
                    model = f"{version} {type_field}"
                else:
                    model = version or type_field or "Standard"
            
            model_name = f"{console_name} {model}".strip()[:200]
            keywords = extract_keywords(model_name)
            normalized = normalize_name(model_name)
            
            cur.execute("""
                INSERT INTO console_variants (console_id, model_name, sku, storage_gb, region, release_date, search_keywords, normalized_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (console_id, model_name[:200], sku[:100] if sku else None, storage_gb, region[:50] if region else None, release[:50] if release else None, keywords, normalized[:200]))
            count += 1
    
    print(f"  Imported {count} variants from {csv_file.name}")
    return count

def import_editions(cur, console_name: str, csv_file: Path):
    """Import editions for a specific console."""
    if not csv_file.exists():
        return 0
    
    # Get console ID
    cur.execute("""
        SELECT id FROM console_reference 
        WHERE name ILIKE %s OR normalized_name ILIKE %s
    """, (f'%{console_name}%', f'%{console_name}%'))
    
    console_row = cur.fetchone()
    if not console_row:
        print(f"  Console '{console_name}' not found in database, skipping {csv_file.name}")
        return 0
    
    console_id = console_row[0]
    count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get('Title', '').strip()
            if not title:
                continue
            
            # Parse price (Loose Price)
            price_str = row.get('Loose Price ▼', row.get('Loose Price', '0')).strip()
            price_str = re.sub(r'[^\d.]', '', price_str)  # Remove $ and commas
            msrp_usd = float(price_str) if price_str else None
            
            # Extract color if mentioned
            color = None
            color_patterns = [
                r'(\w+)\s+Console', r'(\w+)\s+Edition', 
                r'(White|Black|Gray|Blue|Red|Green)', r'(Glacier|Coral|Neon|Turquoise)'
            ]
            for pattern in color_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    color = match.group(1).capitalize()
                    break
            
            # Extract special features
            features = []
            if 'bundle' in title.lower():
                features.append('bundle')
            if 'limited' in title.lower():
                features.append('limited edition')
            if 'development kit' in title.lower() or 'dev kit' in title.lower():
                features.append('development kit')
            
            edition_name = title[:200]
            special_features = (', '.join(features) if features else None)[:200] if features else None
            keywords = extract_keywords(title)
            normalized = normalize_name(title)[:200]
            
            cur.execute("""
                INSERT INTO console_editions (console_id, edition_name, color, special_features, msrp_usd, search_keywords, normalized_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (console_id, edition_name, color[:100] if color else None, special_features, msrp_usd, keywords, normalized))
            count += 1
    
    print(f"  Imported {count} editions from {csv_file.name}")
    return count

def main():
    """Main import function."""
    import psycopg2
    
    print("Connecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    try:
        with conn.cursor() as cur:
            print("\n=== Importing Console Reference Data ===\n")
            
            # Import main consoles
            import_consoles(cur)
            conn.commit()
            
            # Import variants
            print("\n--- Importing Variants ---")
            variant_files = [
                ("PlayStation 3", CONSOLES_DIR / "PS3_variants.csv"),
                ("Nintendo Switch", CONSOLES_DIR / "switch_variants.csv"),
                ("Xbox 360", CONSOLES_DIR / "xbox_360_variants.csv"),
            ]
            
            for console, csv_file in variant_files:
                import_variants(cur, console, csv_file)
            conn.commit()
            
            # Import editions
            print("\n--- Importing Editions ---")
            edition_files = [
                ("PlayStation 2", CONSOLES_DIR / "PS2_editions.csv"),
                ("PlayStation 3", CONSOLES_DIR / "PS3_editions.csv"),
                ("PlayStation 4", CONSOLES_DIR / "PS4_editions.csv"),
                ("Nintendo Switch", CONSOLES_DIR / "switch_editions.csv"),
                ("Xbox 360", CONSOLES_DIR / "xbox_360_editions.csv"),
                ("Xbox", CONSOLES_DIR / "xbox_editions.csv"),
                ("Xbox", CONSOLES_DIR / "xbox_editions2.csv"),
                ("Xbox One", CONSOLES_DIR / "xbox_one_editions.csv"),
            ]
            
            for console, csv_file in edition_files:
                import_editions(cur, console, csv_file)
            conn.commit()
            
            # Add some manual entries for common modern consoles that might not be in CSVs
            print("\n--- Adding Modern Console Data ---")
            
            # Check if PS5 exists, add if not
            cur.execute("SELECT id FROM console_reference WHERE name ILIKE '%playstation 5%'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO console_reference (name, company, generation, search_keywords, normalized_name)
                    VALUES ('PlayStation 5', 'Sony', 5, ARRAY['ps5', 'playstation 5', 'playstation5'], 'playstation 5')
                """)
                print("  Added PlayStation 5")
            
            # Check if Xbox Series X/S exists
            cur.execute("SELECT id FROM console_reference WHERE name ILIKE '%xbox series%'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO console_reference (name, company, generation, search_keywords, normalized_name)
                    VALUES ('Xbox Series X', 'Microsoft', 9, ARRAY['xbox series x', 'series x'], 'xbox series x'),
                           ('Xbox Series S', 'Microsoft', 9, ARRAY['xbox series s', 'series s'], 'xbox series s')
                """)
                print("  Added Xbox Series X/S")
            
            conn.commit()
            
            print("\n=== Import Complete ===")
            
            # Show stats
            cur.execute("SELECT COUNT(*) FROM console_reference")
            console_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM console_variants")
            variant_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM console_editions")
            edition_count = cur.fetchone()[0]
            
            print(f"\nTotal records:")
            print(f"  Consoles: {console_count}")
            print(f"  Variants: {variant_count}")
            print(f"  Editions: {edition_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
