#!/usr/bin/env python
"""Check database state for gfokc listing."""
from src.database.connection import get_session
from sqlalchemy import text

with get_session() as session:
    # Check all versions of gfokc
    rows = session.execute(text("""
        SELECT listing_id, version_number, content_hash, title, price_eur
        FROM listings
        WHERE listing_id = 'gfokc' OR listing_id LIKE 'gfokc_v%'
        ORDER BY version_number
    """)).fetchall()
    
    print(f"Found {len(rows)} rows for gfokc:")
    for row in rows:
        print(f"  ID: {row[0]}, Ver: {row[1]}, Hash: {row[2][:16]}..., Price: €{row[4]}")
        print(f"      Title: {row[3][:60]}...")
        print()
