"""Compare all backup files to find the most complete listings set."""
import sys
from pathlib import Path
import re
from datetime import datetime

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
        return {}
    
    data_section = copy_match.group(2).strip()
    lines = data_section.split('\n')
    
    listings = {}
    for line in lines:
        if not line.strip():
            continue
        values = line.split('\t')
        if len(values) < 2:
            continue
        # listing_id is the second column (index 1) in most backups
        listing_id = values[1] if len(values) > 1 else values[0]
        listings[listing_id] = line
    
    return listings

def compare_all_backups():
    """Find and compare all backup files."""
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        backup_dir = Path(__file__).parent
    
    # Find all backup files
    backup_files = sorted(backup_dir.glob("backup_*.sql"))
    
    if not backup_files:
        print("No backup files found!")
        return
    
    print(f"Found {len(backup_files)} backup files\n")
    print("=" * 80)
    
    # Extract listings from each backup
    all_listings = {}
    backup_stats = []
    
    for backup_file in backup_files:
        listings = extract_listings(str(backup_file))
        all_listings[backup_file.name] = listings
        
        # Parse date from filename
        date_match = re.search(r'backup_(\d{4}-\d{2}-\d{2})', backup_file.name)
        date_str = date_match.group(1) if date_match else "unknown"
        
        backup_stats.append({
            'file': backup_file.name,
            'date': date_str,
            'count': len(listings),
            'listings': set(listings.keys())
        })
        
        print(f"{backup_file.name}: {len(listings)} listings ({date_str})")
    
    print("\n" + "=" * 80)
    print("PAIRWISE COMPARISON (listings unique to older backup):")
    print("=" * 80)
    
    # Compare consecutive backups
    for i in range(len(backup_stats) - 1):
        older = backup_stats[i]
        newer = backup_stats[i + 1]
        
        unique_to_older = older['listings'] - newer['listings']
        unique_to_newer = newer['listings'] - older['listings']
        common = older['listings'] & newer['listings']
        
        print(f"\n{older['file']} vs {newer['file']}:")
        print(f"  Unique to {older['date']}: {len(unique_to_older)} listings")
        print(f"  Unique to {newer['date']}: {len(unique_to_newer)} listings")
        print(f"  Common: {len(common)} listings")
        if len(unique_to_older) > 0:
            print(f"  ⚠️  {len(unique_to_older)} listings LOST between backups!")
    
    # Find the best backup (most unique listings)
    print("\n" + "=" * 80)
    print("UNIQUE LISTINGS PER BACKUP:")
    print("=" * 80)
    
    # Calculate union of all listings
    all_ids = set()
    for stat in backup_stats:
        all_ids.update(stat['listings'])
    
    print(f"\nTotal unique listings across ALL backups: {len(all_ids)}\n")
    
    for stat in backup_stats:
        unique = stat['listings'] - (all_ids - stat['listings'])
        missing = all_ids - stat['listings']
        print(f"{stat['file']}:")
        print(f"  Has: {stat['count']} listings")
        print(f"  Missing: {len(missing)} listings")
        print(f"  Coverage: {len(stat['listings'])}/{len(all_ids)} ({100*len(stat['listings'])/len(all_ids):.1f}%)")
    
    # Recommend the best merge
    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    
    # Find backups with most unique listings
    best_backups = sorted(backup_stats, key=lambda x: x['count'], reverse=True)[:2]
    
    if len(best_backups) >= 2:
        b1, b2 = best_backups[0], best_backups[1]
        merged = b1['listings'] | b2['listings']
        print(f"\nMerge '{b1['file']}' + '{b2['file']}' = {len(merged)} total listings")
        print(f"Run: python merge_backups.py \"{b1['file']}\" \"{b2['file']}\"")

if __name__ == "__main__":
    compare_all_backups()
