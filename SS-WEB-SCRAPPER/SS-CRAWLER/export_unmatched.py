"""Export unmatched and low confidence CPU listings to CSV."""
import csv
import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from sqlalchemy import text

def export_unmatched():
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # 1. Unmatched CPUs
        print("Fetching unmatched CPU listings...")
        unmatched = session.execute(text("""
            SELECT 
                listing_id,
                title,
                description,
                price_eur,
                seller_location,
                date_posted,
                first_seen_at,
                last_seen_at
            FROM listings 
            WHERE category = 'cpu' 
                AND matched_cpu_id IS NULL 
                AND is_active = true
            ORDER BY last_seen_at DESC
        """)).fetchall()
        
        with open('unmatched_cpus.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['listing_id', 'title', 'description', 'price_eur', 
                           'seller_location', 'date_posted', 'first_seen_at', 'last_seen_at'])
            for row in unmatched:
                writer.writerow(row)
        
        print(f"Exported {len(unmatched)} unmatched CPUs to unmatched_cpus.csv")
        
        # 2. Low confidence matches
        print("\nFetching low confidence CPU matches...")
        low_conf = session.execute(text("""
            SELECT 
                l.listing_id,
                l.title,
                l.price_eur,
                l.seller_location,
                l.cpu_confidence_score as confidence,
                l.cpu_match_method as method,
                c.cpu_name,
                c.processor_number,
                c.cores,
                c.threads,
                c.socket,
                l.last_seen_at
            FROM listings l
            LEFT JOIN cpu_reference c ON l.matched_cpu_id = c.id
            WHERE l.category = 'cpu' 
                AND l.matched_cpu_id IS NOT NULL
                AND l.cpu_confidence_score < 0.70
                AND l.is_active = true
            ORDER BY l.cpu_confidence_score ASC
        """)).fetchall()
        
        with open('low_confidence_cpus.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['listing_id', 'title', 'price_eur', 'seller_location',
                           'confidence', 'method', 'cpu_name', 'processor_number',
                           'cores', 'threads', 'socket', 'last_seen_at'])
            for row in low_conf:
                writer.writerow(row)
        
        print(f"Exported {len(low_conf)} low confidence CPUs to low_confidence_cpus.csv")
        
        # 3. Summary
        print("\n--- Summary ---")
        stats = session.execute(text("""
            SELECT 
                CASE 
                    WHEN matched_cpu_id IS NULL THEN 'Unmatched'
                    WHEN cpu_confidence_score < 0.70 THEN 'Low Confidence'
                    ELSE 'Good Match'
                END as match_status,
                COUNT(*) as count
            FROM listings
            WHERE category = 'cpu'
                AND is_active = true
            GROUP BY match_status
        """)).fetchall()
        
        for status, count in stats:
            print(f"  {status}: {count}")

if __name__ == "__main__":
    export_unmatched()
