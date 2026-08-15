# -*- coding: utf-8 -*-
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5433",
    database="ss_market",
    user="crawler",
    password="crawler_pass"
)

def extract_date_from_page(url):
    """Fetch detail page and extract date."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text = soup.get_text()
        
        # Pattern: DD.MM.YYYY
        match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
        
        # Pattern: DD.MM (current year)
        match = re.search(r'(\d{2})\.(\d{2})(?!\.)', text)
        if match:
            day, month = match.groups()
            return datetime(datetime.now().year, int(month), int(day))
        
        return None
    except Exception as e:
        return None

try:
    cursor = conn.cursor()
    
    # Get ALL listings without dates
    cursor.execute("""
        SELECT id, listing_id, listing_url, title
        FROM console_listings
        WHERE date_posted IS NULL
    """)
    
    listings = cursor.fetchall()
    print(f"Found {len(listings)} listings without dates")
    
    updated = 0
    for row in listings:
        listing_id, lid, url, title = row
        
        date = extract_date_from_page(url)
        if date:
            cursor.execute("""
                UPDATE console_listings
                SET date_posted = %s
                WHERE id = %s
            """, (date, listing_id))
            conn.commit()
            updated += 1
            if updated % 10 == 0:
                print(f"Updated {updated}...")
    
    print(f"\nTotal updated: {updated}")
    
    cursor.close()
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
