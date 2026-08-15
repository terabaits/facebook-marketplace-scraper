#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

repo = ConsoleRepository()
repo.load_references()
matcher = ConsoleMatcher(repo.consoles, repo.variants, repo.editions)

try:
    with conn.cursor() as cur:
        # Get ID 205
        cur.execute("""
            SELECT id, listing_id, title, price_eur
            FROM console_listings
            WHERE id = 205
        """)
        
        row = cur.fetchone()
        if not row:
            print("ID 205 not found")
            sys.exit()
            
        listing_id, lid, title, price = row
        print(f"ID 205: {title}")
        print(f"Price: {price}")
        
        # Match
        result = matcher.match(title, "", price=price or 0)
        
        if result.console:
            print(f"✓ MATCHED: {result.console.name} ({result.console_confidence:.0%})")
            
            # Update database
            cur.execute("""
                UPDATE console_listings
                SET matched_console_id = %s,
                    matched_variant_id = %s,
                    matched_edition_id = %s,
                    console_confidence_score = %s,
                    console_match_method = %s,
                    variant_confidence_score = %s,
                    edition_confidence_score = %s
                WHERE id = %s
            """, (
                result.console.id if result.console else None,
                result.variant.id if result.variant else None,
                result.edition.id if result.edition else None,
                result.console_confidence,
                result.method,
                result.variant_confidence,
                result.edition_confidence,
                205
            ))
            conn.commit()
            print("Database updated!")
        else:
            print(f"✗ NO MATCH")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
