#!/usr/bin/env python3
"""Import PSU and Cases from CSV to database"""
import sys
import csv
import re
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

# Clear existing data
try:
    cursor.execute("DELETE FROM listings WHERE matched_case_id IS NOT NULL OR matched_psu_id IS NOT NULL")
    cursor.execute("TRUNCATE TABLE case_reference RESTART IDENTITY CASCADE")
    cursor.execute("TRUNCATE TABLE psu_reference RESTART IDENTITY CASCADE")
    conn.commit()
    print("Cleared existing data")
except Exception as e:
    print(f"Note: {e}")
    conn.rollback()

# Import Cases
cases_file = r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\Cases.csv'
cases_imported = 0
with open(cases_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            rating = row.get('Rating')
            rating_int = int(rating) if rating and rating.strip() and rating.isdigit() else None
            
            price = row.get('Price')
            price_float = float(price) if price and price.strip() else None
            
            name = row.get('Name') or 'Unknown'
            normalized = normalize_text(name)
            
            # Generate search keywords
            keywords = [normalize_text(word) for word in name.split() if len(word) > 2]
            
            cursor.execute("""
                INSERT INTO case_reference (name, type, color, power_supply, side_panel, external_volume, internal_35_bays, rating, price, normalized_name, search_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                row.get('Type') or None,
                row.get('Color') or None,
                row.get('Power Supply') or None,
                row.get('Side Panel') or None,
                row.get('External volume') or None,
                row.get('Internal 3.5" bays') or None,
                rating_int,
                price_float,
                normalized,
                keywords
            ))
            cases_imported += 1
        except Exception as e:
            conn.rollback()
            print(f"Error importing case: {e}")
            continue

conn.commit()

# Import PSUs
psu_file = r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\psu.csv'
psus_imported = 0
with open(psu_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            rating = row.get('Rating')
            rating_int = int(rating) if rating and rating.strip() and rating.isdigit() else None
            
            price = row.get('Price')
            price_float = float(price) if price and price.strip() else None
            
            name = row.get('Name') or 'Unknown'
            normalized = normalize_text(name)
            
            # Generate search keywords
            keywords = [normalize_text(word) for word in name.split() if len(word) > 2]
            
            wattage = row.get('Wattage')
            wattage_str = wattage.replace(' W', '').replace('W', '').strip() if wattage else None
            
            cursor.execute("""
                INSERT INTO psu_reference (name, form_factor, efficiency_rating, wattage, modular, rating, price, normalized_name, search_keywords)
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
            psus_imported += 1
        except Exception as e:
            conn.rollback()
            print(f"Error importing PSU: {e}")
            continue

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM case_reference")
case_count = cursor.fetchone()[0]
print(f"Imported {case_count} cases (attempted {cases_imported})")

cursor.execute("SELECT COUNT(*) FROM psu_reference")
psu_count = cursor.fetchone()[0]
print(f"Imported {psu_count} PSUs (attempted {psus_imported})")

cursor.close()
conn.close()
print("Done!")
