import psycopg2
import json
import sys
from datetime import datetime

def get_current_listings():
    """Get current console listings from database."""
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        database='ss_market',
        user='crawler',
        password='crawler_pass'
    )
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT listing_id, title, price_eur, seller_location, is_active, last_seen_at
        FROM listings 
        WHERE category = 'console'
        ORDER BY listing_id
    ''')
    
    listings = {}
    for row in cursor.fetchall():
        listings[row[0]] = {
            'listing_id': row[0],
            'title': row[1],
            'price_eur': row[2],
            'seller_location': row[3],
            'is_active': row[4],
            'last_seen_at': row[5].isoformat() if row[5] else None
        }
    
    cursor.close()
    conn.close()
    return listings

def load_backup_listings(backup_file):
    """Load console listings from a backup JSON file."""
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        listings = {}
        for item in data:
            if isinstance(item, dict) and item.get('category') == 'console':
                lid = item.get('listing_id')
                if lid:
                    listings[lid] = item
        return listings
    except Exception as e:
        print(f"Error loading backup {backup_file}: {e}")
        return {}

def compare_listings(current, backup, backup_name):
    """Compare current listings with backup to find disappeared ones."""
    disappeared = []
    price_changed = []
    still_present = []
    
    for lid, backup_item in backup.items():
        if lid in current:
            current_item = current[lid]
            still_present.append({
                'listing_id': lid,
                'title': backup_item.get('title', 'Unknown'),
                'backup_price': backup_item.get('price_eur'),
                'current_price': current_item['price_eur'],
                'price_diff': current_item['price_eur'] - backup_item.get('price_eur', 0) if backup_item.get('price_eur') else None
            })
            
            # Check for price changes
            backup_price = backup_item.get('price_eur')
            current_price = current_item['price_eur']
            if backup_price and current_price and abs(backup_price - current_price) > 0.01:
                price_changed.append({
                    'listing_id': lid,
                    'title': backup_item.get('title', 'Unknown'),
                    'old_price': backup_price,
                    'new_price': current_price,
                    'change_pct': round(((current_price - backup_price) / backup_price) * 100, 1)
                })
        else:
            disappeared.append({
                'listing_id': lid,
                'title': backup_item.get('title', 'Unknown'),
                'price': backup_item.get('price_eur'),
                'seller_location': backup_item.get('seller_location'),
                'last_seen': backup_item.get('last_seen_at')
            })
    
    return disappeared, price_changed, still_present

def main():
    print("=" * 70)
    print("CONSOLE LISTINGS COMPARISON TOOL")
    print("=" * 70)
    print()
    
    # Get current listings
    print("Fetching current console listings from database...")
    current = get_current_listings()
    print(f"Current console listings in database: {len(current)}")
    print()
    
    if len(current) == 0:
        print("WARNING: No console listings found in the database!")
        print()
    
    # Load backups from command line
    backups = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not backups:
        print("Usage: python compare_console_backups.py <backup1.json> <backup2.json> ...")
        print()
        print("To export console listings from database for comparison:")
        print("  SELECT json_agg(l.*) FROM listings l WHERE category='console'")
        return
    
    all_disappeared = {}
    all_price_changes = {}
    
    for backup_file in backups:
        print(f"\nLoading backup: {backup_file}")
        backup = load_backup_listings(backup_file)
        print(f"  Console listings in backup: {len(backup)}")
        
        disappeared, price_changed, still_present = compare_listings(current, backup, backup_file)
        
        all_disappeared[backup_file] = disappeared
        all_price_changes[backup_file] = price_changed
        
        print(f"  Still present: {len(still_present)}")
        print(f"  Disappeared: {len(disappeared)}")
        print(f"  Price changed: {len(price_changed)}")
    
    # Summary report
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    
    for backup_file in backups:
        disappeared = all_disappeared.get(backup_file, [])
        price_changed = all_price_changes.get(backup_file, [])
        
        print(f"\n📁 Backup: {backup_file}")
        print("-" * 50)
        
        if disappeared:
            print(f"\n  ❌ DISAPPEARED LISTINGS ({len(disappeared)}):")
            for item in disappeared[:10]:  # Show first 10
                print(f"     • {item['listing_id']}: {item['title'][:50]}... (€{item['price']})")
            if len(disappeared) > 10:
                print(f"     ... and {len(disappeared) - 10} more")
        else:
            print(f"\n  ✅ No listings disappeared from this backup")
        
        if price_changed:
            print(f"\n  💰 PRICE CHANGES ({len(price_changed)}):")
            for item in price_changed[:10]:
                change_symbol = "📈" if item['change_pct'] > 0 else "📉"
                print(f"     • {item['listing_id']}: €{item['old_price']} → €{item['new_price']} ({change_symbol} {item['change_pct']}%)")
            if len(price_changed) > 10:
                print(f"     ... and {len(price_changed) - 10} more")
    
    # Cross-backup analysis
    if len(backups) > 1:
        print("\n" + "=" * 70)
        print("CROSS-BACKUP ANALYSIS")
        print("=" * 70)
        
        # Find listings that disappeared from ALL backups
        all_ids = set()
        for backup_file in backups:
            backup = load_backup_listings(backup_file)
            all_ids.update(backup.keys())
        
        permanently_gone = []
        for lid in all_ids:
            if lid not in current:
                # Check if it existed in any backup
                for backup_file in backups:
                    backup = load_backup_listings(backup_file)
                    if lid in backup:
                        permanently_gone.append({
                            'listing_id': lid,
                            'title': backup[lid].get('title', 'Unknown'),
                            'source_backup': backup_file
                        })
                        break
        
        if permanently_gone:
            print(f"\n  ❌ Listings gone from ALL backups ({len(permanently_gone)}):")
            for item in permanently_gone[:15]:
                print(f"     • {item['listing_id']}: {item['title'][:50]}...")
        else:
            print("\n  ✅ All listings from backups are still in database or newer backups")

if __name__ == '__main__':
    main()
