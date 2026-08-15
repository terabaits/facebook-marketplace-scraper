"""Merge listings from both backups - keep all unique listings."""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def extract_listings(backup_file: str) -> dict:
    """Extract all listings from a backup file as dict keyed by listing_id."""
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the COPY section for listings
    copy_match = re.search(
        r'COPY public\.listings \(([^)]+)\) FROM stdin;\n(.*?)\\\.',
        content,
        re.DOTALL
    )
    
    if not copy_match:
        print(f"No listings COPY section in {backup_file}")
        return {}
    
    columns = [c.strip() for c in copy_match.group(1).split(',')]
    data_section = copy_match.group(2).strip()
    lines = data_section.split('\n')
    
    listings = {}
    listing_id_idx = columns.index('listing_id')
    
    for line in lines:
        if not line.strip():
            continue
        values = line.split('\t')
        if len(values) != len(columns):
            continue
        
        listing_id = values[listing_id_idx]
        # Store as dict
        listing = {}
        for i, col in enumerate(columns):
            val = values[i]
            if val == '\\N':
                listing[col] = None
            else:
                listing[col] = val
        listings[listing_id] = listing
    
    return listings

def merge_backups(backup1: str, backup2: str):
    """Merge listings from both backups into database."""
    print(f"Reading {backup1}...")
    listings1 = extract_listings(backup1)
    print(f"  Found {len(listings1)} listings")
    
    print(f"\nReading {backup2}...")
    listings2 = extract_listings(backup2)
    print(f"  Found {len(listings2)} listings")
    
    # Merge - keep all unique listings
    merged = {**listings1, **listings2}
    
    # Count stats
    only_in_1 = set(listings1.keys()) - set(listings2.keys())
    only_in_2 = set(listings2.keys()) - set(listings1.keys())
    common = set(listings1.keys()) & set(listings2.keys())
    
    print("\n" + "=" * 60)
    print("MERGE SUMMARY:")
    print("=" * 60)
    print(f"From {Path(backup1).name}: {len(listings1)} listings")
    print(f"  - Unique: {len(only_in_1)}")
    print(f"  - Common: {len(common)}")
    print(f"\nFrom {Path(backup2).name}: {len(listings2)} listings")
    print(f"  - Unique: {len(only_in_2)}")
    print(f"  - Common: {len(common)}")
    print(f"\n→ Total merged: {len(merged)} listings")
    
    # Insert into database
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    print("\nClearing current listings...")
    with get_session() as session:
        session.execute(text("DELETE FROM listing_versions"))
        session.execute(text("DELETE FROM listings"))
        session.commit()
    
    print(f"Inserting {len(merged)} merged listings...")
    inserted = 0
    failed = 0
    
    with get_session() as session:
        for listing_id, listing in merged.items():
            try:
                # Get columns and values
                columns = list(listing.keys())
                values = [listing[col] for col in columns]
                
                # Build INSERT
                col_names = ', '.join(columns)
                placeholders = ', '.join([f':{c}' for c in columns])
                
                sql = f"INSERT INTO listings ({col_names}) VALUES ({placeholders})"
                session.execute(text(sql), listing)
                inserted += 1
                
                if inserted % 100 == 0:
                    session.commit()
                    print(f"  Inserted {inserted}/{len(merged)}...")
                    
            except Exception as e:
                failed += 1
                if failed < 5:
                    print(f"  Error on {listing_id}: {e}")
        
        session.commit()
    
    print(f"\n✓ Merge complete!")
    print(f"  Inserted: {inserted}")
    print(f"  Failed: {failed}")
    print(f"\nRun 'python check_db.py' to verify.")

if __name__ == "__main__":
    backup1 = sys.argv[1] if len(sys.argv) > 1 else "backup_2026-05-04_215040.sql"
    backup2 = sys.argv[2] if len(sys.argv) > 2 else "backup_2026-05-17_030733.sql"
    
    merge_backups(backup1, backup2)
