#!/usr/bin/env python3
"""Run lens scraper and save to database."""

import sys
sys.path.insert(0, 'G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER')

import os
import psycopg2
from datetime import datetime
from lens_scraper_standalone import LensScraper, LensListing

DB_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 5433)),
    'database': os.environ.get('DATABASE_NAME', 'ss_market'),
    'user': os.environ.get('DATABASE_USER', 'crawler'),
    'password': os.environ.get('DATABASE_PASSWORD', 'crawler_pass')
}

def save_listings_to_db(listings):
    """Save lens listings to database."""
    if not listings:
        print("No listings to save")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    saved = 0
    updated = 0
    
    for listing in listings:
        try:
            # Check if listing exists
            cursor.execute(
                "SELECT id FROM listings WHERE listing_id = %s",
                (listing.listing_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE listings SET
                        title = %s,
                        description = %s,
                        price_eur = %s,
                        seller_location = %s,
                        date_posted = %s,
                        is_active = true,
                        last_seen_at = NOW(),
                        matched_lens_id = %s,
                        lens_confidence_score = %s,
                        lens_match_method = %s,
                        category = 'lens'
                    WHERE listing_id = %s
                """, (
                    listing.title,
                    listing.description,
                    listing.price_eur,
                    listing.location,
                    listing.posted_date if listing.posted_date else datetime.now(),
                    listing.matched_lens_id,
                    listing.confidence_score,
                    listing.match_method,
                    listing.listing_id
                ))
                updated += 1
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur,
                        seller_location, date_posted, listing_url,
                        is_active, category, matched_lens_id,
                        lens_confidence_score, lens_match_method,
                        first_seen_at, last_seen_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    listing.listing_id,
                    listing.title,
                    listing.description,
                    listing.price_eur,
                    listing.location,
                    listing.posted_date if listing.posted_date else datetime.now(),
                    listing.url,
                    True,
                    'lens',
                    listing.matched_lens_id,
                    listing.confidence_score,
                    listing.match_method
                ))
                saved += 1
                
        except Exception as e:
            print(f"Error saving {listing.listing_id}: {e}")
            conn.rollback()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Saved: {saved} new, Updated: {updated} existing")

def main():
    print("Lens Scraper - SS.COM")
    print("=" * 60)
    
    scraper = LensScraper()
    
    # Scrape 1 page (for testing)
    print("\nScraping lens listings...")
    listings = scraper.scrape_category(max_pages=1, limit=0)
    
    if listings:
        print(f"\nExporting to CSV...")
        scraper.export_to_csv(listings, "lens_listings.csv")
        
        print(f"\nSaving to database...")
        save_listings_to_db(listings)
    
    print("\n" + "=" * 60)
    print("Scraping complete!")

if __name__ == "__main__":
    main()
