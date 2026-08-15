#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix existing unmatched listings by fetching console type from detail pages."""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import re
import requests
from bs4 import BeautifulSoup
import psycopg2
from src.database.console_repository import ConsoleRepository
from src.scraper.console_matcher import ConsoleMatcher

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
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Load matcher
repo = ConsoleRepository()
repo.load_references()
matcher = ConsoleMatcher(repo.consoles, repo.variants, repo.editions)

try:
    with conn.cursor() as cur:
        # Get unmatched listings
        cur.execute("""
            SELECT id, listing_id, listing_url, title, price_eur
            FROM console_listings
            WHERE matched_console_id IS NULL
            ORDER BY id
        """)
        
        listings = cur.fetchall()
        print(f"Found {len(listings)} unmatched listings")
        
        matched = 0
        for row in listings:
            listing_id, lid, url, title, price = row
            
            # Fetch console type
            console_type = get_console_type(url)
            if console_type:
                full_title = f"{title} {console_type}"
                print(f"\nID {listing_id}: {full_title}")
                
                # Match with console type
                result = matcher.match(full_title, "", price=price or 0)
                
                if result.console:
                    print(f"  ✓ MATCHED: {result.console.name}")
                    
                    # Update database
                    cur.execute("""
                        UPDATE console_listings
                        SET matched_console_id = %s,
                            matched_variant_id = %s,
                            matched_edition_id = %s,
                            console_confidence_score = %s,
                            console_match_method = %s,
                            variant_confidence_score = %s,
                            edition_confidence_score = %s,
                            title = %s
                        WHERE id = %s
                    """, (
                        result.console.id,
                        result.variant.id if result.variant else None,
                        result.edition.id if result.edition else None,
                        result.console_confidence,
                        result.method,
                        result.variant_confidence,
                        result.edition_confidence,
                        full_title,
                        listing_id
                    ))
                    conn.commit()
                    matched += 1
                else:
                    print(f"  ✗ No match")
        
        print(f"\nMatched {matched} listings")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
