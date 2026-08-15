#!/usr/bin/env python3
"""Standalone script to run the computer scraper."""
import sys
import argparse

from src.scraper.computer_scraper import ComputerScraper
from src.database.connection import init_database
from src.utils.config import AppConfig


def main():
    parser = argparse.ArgumentParser(description='Scrape computer listings from ss.com')
    parser.add_argument('--test', '-t', action='store_true', help='Test mode - fetch fewer listings')
    parser.add_argument('--limit', '-l', type=int, default=0, help='Maximum listings to scrape')
    parser.add_argument('--max-pages', '-p', type=int, default=5, help='Maximum pages to scrape')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Parse only, do not save')
    parser.add_argument('--url', '-u', type=str, help='Test single URL')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Computer Scraper for SS-Crawler")
    print("=" * 60)
    
    config = AppConfig.from_yaml()
    
    if args.test:
        config.scraper.test_mode = True
        print("TEST MODE ENABLED")
    
    if args.limit > 0:
        config.scraper.max_listings = args.limit
        print(f"Limit: {args.limit} listings")
    
    if args.max_pages >= 0:
        config.scraper.max_pages = args.max_pages
        if args.max_pages == 0:
            print("Pages: unlimited")
        else:
            print(f"Pages: {args.max_pages}")
    
    if args.dry_run:
        print("DRY RUN - will not save to database")
    
    print("-" * 60)
    
    scraper = ComputerScraper(config)
    
    if args.url:
        # Test single URL
        scraper.initialize()
        listing = scraper.scrape_single(args.url)
        if listing:
            print(f"\nSuccessfully scraped: {listing.title}")
            print(f"Price: €{listing.price_eur:.2f}")
            if listing.matched_cpu_id:
                print(f"CPU ID: {listing.matched_cpu_id}")
            if listing.matched_gpu_id:
                print(f"GPU ID: {listing.matched_gpu_id}")
    else:
        # Full scrape
        stats = scraper.run()
        
        print("\n" + "=" * 60)
        print("COMPUTER SCRAPE SUMMARY")
        print("=" * 60)
        print(f"Total processed:     {stats['total']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Skipped:             {stats['skipped']}")
        print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())