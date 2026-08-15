"""Compare listings between two backup files."""
import sys
from pathlib import Path
import re

def extract_listing_ids(backup_file: str):
    """Extract all listing_ids from a backup file."""
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the COPY section for listings
    copy_match = re.search(
        r'COPY public\.listings \([^)]+\) FROM stdin;\n(.*?)\\\.',
        content,
        re.DOTALL
    )
    
    if not copy_match:
        print(f"No listings COPY section in {backup_file}")
        return set()
    
    data_section = copy_match.group(1).strip()
    lines = data_section.split('\n')
    
    # Extract column names to find listing_id position
    header_match = re.search(r'COPY public\.listings \(([^)]+)\) FROM', content)
    columns = [c.strip() for c in header_match.group(1).split(',')]
    
    try:
        listing_id_idx = columns.index('listing_id')
    except ValueError:
        print(f"listing_id column not found in {backup_file}")
        return set()
    
    # Extract listing_ids
    listing_ids = set()
    for line in lines:
        if not line.strip():
            continue
        values = line.split('\t')
        if len(values) > listing_id_idx:
            listing_ids.add(values[listing_id_idx])
    
    return listing_ids

def compare_backups(backup1: str, backup2: str):
    """Compare listings between two backups."""
    print(f"Extracting listings from {backup1}...")
    ids1 = extract_listing_ids(backup1)
    print(f"  Found {len(ids1)} listings")
    
    print(f"\nExtracting listings from {backup2}...")
    ids2 = extract_listing_ids(backup2)
    print(f"  Found {len(ids2)} listings")
    
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS:")
    print("=" * 60)
    
    # Listings only in backup1 (older)
    only_in_1 = ids1 - ids2
    if only_in_1:
        print(f"\n✓ Listings in {Path(backup1).name} but NOT in {Path(backup2).name}: {len(only_in_1)}")
        sample = list(only_in_1)[:5]
        print(f"  Sample IDs: {sample}")
    else:
        print(f"\n✗ No unique listings in {Path(backup1).name}")
    
    # Listings only in backup2 (newer)
    only_in_2 = ids2 - ids1
    if only_in_2:
        print(f"\n✓ Listings in {Path(backup2).name} but NOT in {Path(backup1).name}: {len(only_in_2)}")
        sample = list(only_in_2)[:5]
        print(f"  Sample IDs: {sample}")
    else:
        print(f"\n✗ No unique listings in {Path(backup2).name}")
    
    # Common listings
    common = ids1 & ids2
    print(f"\n• Common listings in both: {len(common)}")
    
    print("\n" + "=" * 60)
    if len(ids1) > len(ids2):
        print(f"Result: {Path(backup1).name} has MORE listings ({len(ids1)} vs {len(ids2)})")
        print(f"       Missing {len(only_in_1)} listings in newer backup!")
    elif len(ids2) > len(ids1):
        print(f"Result: {Path(backup2).name} has MORE listings ({len(ids2)} vs {len(ids1)})")
    else:
        print(f"Result: Both backups have same number of listings ({len(ids1)})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_backups.py backup1.sql backup2.sql")
        print("\nUsing default backups...")
        backup1 = "backup_2026-05-04_215040.sql"
        backup2 = "backup_2026-05-17_030733.sql"
    else:
        backup1 = sys.argv[1]
        backup2 = sys.argv[2]
    
    compare_backups(backup1, backup2)
