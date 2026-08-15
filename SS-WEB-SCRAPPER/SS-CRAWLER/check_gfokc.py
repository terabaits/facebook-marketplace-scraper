#!/usr/bin/env python
"""Check database state."""
import sys
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER')

from src.database.connection import get_session
from sqlalchemy import text

with get_session() as session:
    # Check all versions of gfokc
    rows = session.execute(text("""
        SELECT listing_id, version_number, content_hash, title, price_eur
        FROM listings
        WHERE listing_id = 'gfokc' OR listing_id LIKE 'gfokc_v%'
        ORDER BY listing_id
    """)).fetchall()
    
    print(f"Found {len(rows)} rows for gfokc:")
    for row in rows:
        hash_val = row[2][:20] if row[2] else "NULL"
        print(f"  ID: {row[0]}, ver={row[1]}, hash={hash_val}..., price=€{row[4]}")
        print(f"      Title: {row[3][:50]}...")
        print()
