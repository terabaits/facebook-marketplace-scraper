"""Export database tables to CSV files as backup."""
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

def export_table_to_csv(cursor, table_name, query=None, filename=None):
    """Export a table to CSV file."""
    if filename is None:
        filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if query is None:
        query = f"SELECT * FROM {table_name}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠️  {table_name}: No data found")
        return 0
    
    # Get column names
    colnames = [desc[0] for desc in cursor.description]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(colnames)
        writer.writerows(rows)
    
    print(f"  ✓ {table_name}: {len(rows)} rows exported to {filename}")
    return len(rows)

def main():
    print("=" * 60)
    print("Database Export to CSV")
    print("=" * 60)
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        total_rows = 0
        
        # Export reference tables
        print("\n📦 Reference Tables:")
        total_rows += export_table_to_csv(cursor, 'gpu_reference')
        total_rows += export_table_to_csv(cursor, 'cpu_reference')
        total_rows += export_table_to_csv(cursor, 'ssd_reference')
        total_rows += export_table_to_csv(cursor, 'ram_reference')
        total_rows += export_table_to_csv(cursor, 'psu_reference')
        total_rows += export_table_to_csv(cursor, 'case_reference')
        
        # Export listings
        print("\n📝 Listings:")
        total_rows += export_table_to_csv(
            cursor, 'listings',
            query="""
                SELECT 
                    listing_id, title, description, price_eur, seller_location,
                    listing_url, image_url, date_posted, category,
                    matched_gpu_id, confidence_score, match_method,
                    matched_cpu_id, cpu_confidence_score, cpu_match_method,
                    matched_ssd_id, ssd_confidence_score, ssd_match_method,
                    matched_ram_id, ram_confidence_score, ram_match_method,
                    matched_psu_id, psu_confidence_score, psu_match_method,
                    matched_case_id, case_confidence_score, case_match_method,
                    is_active, first_seen_at, last_seen_at
                FROM listings
                ORDER BY last_seen_at DESC
            """
        )
        
        # Export price history
        print("\n💰 Price History:")
        total_rows += export_table_to_csv(cursor, 'price_history')
        
        # Export scrape runs
        print("\n🔧 Scrape Runs:")
        total_rows += export_table_to_csv(cursor, 'scrape_runs')
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"✓ Export complete! Total rows exported: {total_rows}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
