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
        
        # Look for date in page text
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
        print(f"Error fetching {url}: {e}")
        return None

try:
    cursor = conn.cursor()
    
    # Get listings without dates
    cursor.execute("""
        SELECT id, listing_id, listing_url, title
        FROM console_listings
        WHERE date_posted IS NULL AND is_active = TRUE
        LIMIT 20
    """)
    
    listings = cursor.fetchall()
    print(f"Found {len(listings)} listings without dates")
    
    updated = 0
    for row in listings:
        listing_id, lid, url, title = row
        print(f"\nProcessing: {title[:40]}...")
        
        date = extract_date_from_page(url)
        if date:
            print(f"  Found date: {date}")
            cursor.execute("""
                UPDATE console_listings
                SET date_posted = %s
                WHERE id = %s
            """, (date, listing_id))
            conn.commit()
            updated += 1
        else:
            print(f"  No date found")
    
    print(f"\nUpdated {updated} listings with dates")
    
    cursor.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
