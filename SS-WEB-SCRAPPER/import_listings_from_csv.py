"""Import listings from CSV file (for recovery)."""
import os
import csv
import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 5433)),
    'database': os.environ.get('DATABASE_NAME', 'ss_market'),
    'user': os.environ.get('DATABASE_USER', 'crawler'),
    'password': os.environ.get('DATABASE_PASSWORD', 'crawler_pass')
}

def import_listings(csv_file, dry_run=True):
    """Import listings from CSV file."""
    print(f"\n📥 Importing from: {csv_file}")
    print(f"   Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE IMPORT'}")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    errors = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                listing_id = row['listing_id']
                
                # Check if already exists
                cursor.execute("SELECT 1 FROM listings WHERE listing_id = %s", (listing_id,))
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                if dry_run:
                    imported += 1
                    continue
                
                # Insert the listing
                cursor.execute("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_gpu_id, confidence_score, match_method,
                        matched_cpu_id, cpu_confidence_score, cpu_match_method,
                        matched_ssd_id, ssd_confidence_score, ssd_match_method,
                        matched_ram_id, ram_confidence_score, ram_match_method,
                        matched_psu_id, psu_confidence_score, psu_match_method,
                        matched_case_id, case_confidence_score, case_match_method,
                        is_active, first_seen_at, last_seen_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                """, (
                    listing_id,
                    row.get('title', ''),
                    row.get('description', ''),
                    float(row['price_eur']) if row.get('price_eur') else None,
                    row.get('seller_location'),
                    row.get('listing_url', ''),
                    row.get('image_url'),
                    row.get('date_posted'),
                    row.get('category', 'gpu'),
                    row.get('matched_gpu_id'),
                    float(row['confidence_score']) if row.get('confidence_score') else None,
                    row.get('match_method'),
                    row.get('matched_cpu_id'),
                    float(row['cpu_confidence_score']) if row.get('cpu_confidence_score') else None,
                    row.get('cpu_match_method'),
                    row.get('matched_ssd_id'),
                    float(row['ssd_confidence_score']) if row.get('ssd_confidence_score') else None,
                    row.get('ssd_match_method'),
                    row.get('matched_ram_id'),
                    float(row['ram_confidence_score']) if row.get('ram_confidence_score') else None,
                    row.get('ram_match_method'),
                    row.get('matched_psu_id'),
                    float(row['psu_confidence_score']) if row.get('psu_confidence_score') else None,
                    row.get('psu_match_method'),
                    row.get('matched_case_id'),
                    float(row['case_confidence_score']) if row.get('case_confidence_score') else None,
                    row.get('case_match_method'),
                    row.get('is_active', 'true').lower() == 'true',
                    row.get('first_seen_at'),
                    row.get('last_seen_at')
                ))
                
                imported += 1
                
                if imported % 100 == 0:
                    print(f"   ... {imported} imported")
                    
            except Exception as e:
                errors += 1
                print(f"   ⚠️  Error importing {listing_id}: {e}")
    
    if not dry_run:
        conn.commit()
    
    cursor.close()
    conn.close()
    
    print(f"\n   Results: {imported} imported, {skipped} skipped (already exist), {errors} errors")
    return imported

def main():
    import sys
    
    print("=" * 60)
    print("Import Listings from CSV")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python import_listings_from_csv.py <csv_file> [--live]")
        print("\nOptions:")
        print("  --live    Actually import (default is dry run)")
        print("\nExample:")
        print("  python import_listings_from_csv.py listings_20240426_143000.csv")
        print("  python import_listings_from_csv.py listings_20240426_143000.csv --live")
        return 1
    
    csv_file = sys.argv[1]
    dry_run = '--live' not in sys.argv
    
    if not os.path.exists(csv_file):
        print(f"\n❌ File not found: {csv_file}")
        return 1
    
    import_listings(csv_file, dry_run)
    
    print("\n" + "=" * 60)
    if dry_run:
        print("✓ Dry run complete. Add --live to actually import.")
    else:
        print("✓ Import complete!")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    exit(main())
