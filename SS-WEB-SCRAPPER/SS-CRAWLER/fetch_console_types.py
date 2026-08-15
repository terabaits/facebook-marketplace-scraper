#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch detail pages for unmatched listings to get 'Konsoles tips'"""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import re
import requests
from bs4 import BeautifulSoup
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5433",
    dbname="ss_market",
    user="crawler",
    password="crawler_pass"
)

def get_console_type(url):
    """Fetch detail page and extract console type."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for "Konsoles tips:" row
        for row in soup.find_all('tr'):
            label = row.find('td', class_='ads_opt_name')
            if label and 'konsoles' in label.get_text(strip=True).lower():
                value = row.find('td', class_='ads_opt')
                if value:
                    return value.get_text(strip=True)
        
        # Also check title
        title_elem = soup.find('title')
        if title_elem:
            return title_elem.get_text()
            
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

try:
    with conn.cursor() as cur:
        # Get unmatched listings
        cur.execute("""
            SELECT id, listing_id, listing_url, title
            FROM console_listings
            WHERE matched_console_id IS NULL
            ORDER BY id
            LIMIT 20
        """)
        
        listings = cur.fetchall()
        print(f"Found {len(listings)} unmatched listings")
        
        for row in listings:
            listing_id, lid, url, title = row
            print(f"\nID {listing_id}: {title[:50]}...")
            
            console_type = get_console_type(url)
            if console_type:
                print(f"  Console type: {console_type}")
            else:
                print(f"  No console type found")
                
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
