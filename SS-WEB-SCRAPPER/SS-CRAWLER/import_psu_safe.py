#!/usr/bin/env python3
"""Import PSU from CSV to database (SAFE - doesn't touch listings)"""
import sys
import csv
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

import psycopg2
from utils.config import AppConfig
from src.utils.text import normalize_text

config = AppConfig.from_yaml(r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\config.yaml')
conn = psycopg2.connect(
    host=config.database.host,
    port=config.database.port,
    database=config.database.name,
    user=config.database.user,
    password=config.database.password
)
cursor = conn.cursor()

# Use DELETE instead of TRUNCATE (safer, no CASCADE)
print("Clearing PSU reference table...")
cursor.execute("DELETE FROM psu_reference")
conn.commit()

# Import PSUs from CSV
psu_file = r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\psu.csv'
imported = 0
with open(psu_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            name = row.get('Name', '').strip()
            if not name:
                continue
                
            normalized = normalize_text(name)
            keywords = [normalize_text(word) for word in name.split() if len(word) > 2]
            
            rating = row.get('Rating', '').strip()
            rating_int = int(rating) if rating and rating.isdigit() else None
            
            price = row.get('Price', '').strip()
            price_float = float(price) if price else None
            
            wattage = row.get('Wattage', '').strip()
            wattage_str = wattage.replace(' W', '').replace('W', '').strip() if wattage else None
            
            cursor.execute("""
                INSERT INTO psu_reference 
                (name, form_factor, efficiency_rating, wattage, modular, rating, price, normalized_name, search_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                row.get('Form Factor') or None,
                row.get('Efficiency Rating') or None,
                wattage_str,
                row.get('Modular') or None,
                rating_int,
                price_float,
                normalized,
                keywords
            ))
            imported += 1
        except Exception as e:
            print(f"Error importing: {row.get('Name')}: {e}")
            continue

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM psu_reference")
count = cursor.fetchone()[0]
print(f"\nImported {count} PSUs")

# Check for System Power 7
print("\nChecking for System Power 7:")
cursor.execute("""
    SELECT name, wattage 
    FROM psu_reference 
    WHERE name ILIKE '%system power 7%'
""")
results = cursor.fetchall()
if results:
    for row in results:
        print(f"  {row[0]} - {row[1]}W")
else:
    print("  Not found!")

cursor.close()
conn.close()
print("\nDone!")
