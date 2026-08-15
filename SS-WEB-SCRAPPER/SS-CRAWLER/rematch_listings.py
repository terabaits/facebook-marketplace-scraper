#!/usr/bin/env python3
"""Re-match existing console listings that don't have matched_console_id."""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

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

# Load matcher
repo = ConsoleRepository()
repo.load_references()
matcher = ConsoleMatcher(repo.consoles, repo.variants, repo.editions)

try:
    with conn.cursor() as cur:
        # Get unmatched listings
        cur.execute("""
            SELECT id, listing_id, title, price_eur
            FROM console_listings
            WHERE matched_console_id IS NULL
            ORDER BY id
        """)
        
        unmatched = cur.fetchall()
        print(f"Found {len(unmatched)} unmatched listings")
        
        matched = 0
        for row in unmatched:
            listing_id, lid, title, price = row
            
            # Match
            result = matcher.match(title, "", price=price or 0)
            
            if result.console:
                # Update database
                cur.execute("""
                    UPDATE console_listings
                    SET matched_console_id = %s,
                        console_confidence_score = %s,
                        console_match_method = %s
                    WHERE id = %s
                """, (
                    result.console.id,
                    result.console_confidence,
                    result.method,
                    listing_id
                ))
                conn.commit()
                
                matched += 1
                print(f"✓ ID {listing_id}: {result.console.name} ({result.console_confidence:.0%})")
                print(f"  Title: {title[:60]}")
            else:
                print(f"✗ ID {listing_id}: No match")
                print(f"  Title: {title[:60]}")
        
        print(f"\nMatched {matched}/{len(unmatched)} listings")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
