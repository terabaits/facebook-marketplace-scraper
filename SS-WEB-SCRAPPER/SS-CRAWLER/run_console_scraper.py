"""Runner script for console scraper."""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scraper.console_scraper import ConsoleScraper
from src.scraper.console_matcher import ConsoleMatcher
from src.database.console_repository import ConsoleRepository
from src.models.schemas import ConsoleListing
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger("console_runner")


def run_console_scraper(max_pages: int = None, fetch_descriptions: bool = False):
    """Run the console scraper."""
    logger.info("=" * 60)
    logger.info("Starting Console Scraper")
    logger.info("=" * 60)
    
    # Load configuration
    config = AppConfig.from_yaml("config.yaml")
    
    # Initialize components
    scraper = ConsoleScraper(config)
    repository = ConsoleRepository()
    
    # Load reference data
    logger.info("Loading console reference data...")
    consoles, variants, editions = repository.load_references()
    
    # Initialize matcher
    matcher = ConsoleMatcher(consoles, variants, editions)
    
    # Start scrape run
    run_id = repository.start_scrape_run()
    logger.info(f"Started scrape run ID: {run_id}")
    
    stats = {
        'total': 0,
        'new': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0,
        'special_editions': 0
    }
    
    try:
        # Scrape listings
        raw_listings = scraper.scrape_listings(max_pages=max_pages)
        stats['total'] = len(raw_listings)
        
        logger.info(f"Processing {len(raw_listings)} listings...")
        
        for i, raw in enumerate(raw_listings):
            try:
                logger.debug(f"Processing listing {i+1}/{len(raw_listings)}: {raw['listing_id']}")
                
                # Fetch description if requested
                description = ""
                if fetch_descriptions:
                    description = scraper.fetch_description(raw['listing_url'])
                
                # Create listing object
                listing = ConsoleListing(
                    listing_id=raw['listing_id'],
                    title=raw['title'],
                    description=description,
                    price_eur=raw['price_eur'],
                    seller_location=raw['seller_location'],
                    listing_url=raw['listing_url'],
                    image_url=raw['image_url'],
                    local_image_path=raw.get('local_image_path'),
                    date_posted=raw['date_posted'],
                    content_hash=raw['content_hash']
                )
                
                # Match to console reference
                match_result = matcher.match(raw['title'], description)
                
                # Log match
                repository.log_match(run_id, raw['listing_id'], raw['title'], match_result)
                
                # Track special editions
                if match_result.is_special:
                    stats['special_editions'] += 1
                    logger.info(f"Special edition detected: {raw['title'][:60]}...")
                
                # Save listing
                if repository.save_listing(listing, match_result):
                    stats['new'] += 1
                else:
                    stats['updated'] += 1
                
            except Exception as e:
                logger.error(f"Error processing listing {raw.get('listing_id', 'unknown')}: {e}")
                stats['failed'] += 1
                continue
        
        logger.info("=" * 60)
        logger.info("Scrape Complete!")
        logger.info(f"  Total listings: {stats['total']}")
        logger.info(f"  New listings: {stats['new']}")
        logger.info(f"  Updated listings: {stats['updated']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Special editions detected: {stats['special_editions']}")
        logger.info("=" * 60)
        
        # Complete scrape run
        repository.complete_scrape_run(run_id, stats)
        
    except Exception as e:
        logger.error(f"Scrape run failed: {e}")
        repository.complete_scrape_run(run_id, stats, error=str(e))
        raise


def show_stats():
    """Show console listing statistics."""
    repository = ConsoleRepository()
    stats = repository.get_stats()
    
    print("\n" + "=" * 60)
    print("Console Listing Statistics")
    print("=" * 60)
    print(f"Total active listings: {stats.get('total_listings', 0)}")
    print(f"Special editions: {stats.get('special_editions', 0)}")
    
    print("\nBy Console:")
    for console, count in stats.get('by_console', []):
        print(f"  {console}: {count}")
    
    print("\nAverage Prices:")
    for console, price in stats.get('avg_prices', []):
        print(f"  {console}: €{price:.2f}")
    
    print("=" * 60)


def test_matcher(title: str):
    """Test the console matcher with a title."""
    repository = ConsoleRepository()
    consoles, variants, editions = repository.load_references()
    matcher = ConsoleMatcher(consoles, variants, editions)
    
    result = matcher.match(title)
    
    print(f"\nInput: {title}")
    print(f"Console: {result.console.name if result.console else 'None'} ({result.console_confidence:.2f})")
    print(f"Variant: {result.variant.model_name if result.variant else 'None'} ({result.variant_confidence:.2f})")
    print(f"Edition: {result.edition.edition_name if result.edition else 'None'} ({result.edition_confidence:.2f})")
    print(f"Method: {result.method}")
    print(f"Special: {result.is_special} - {result.special_note}")


def main():
    parser = argparse.ArgumentParser(description='Console Scraper for ss.com')
    parser.add_argument('--pages', type=int, help='Maximum number of pages to scrape')
    parser.add_argument('--descriptions', action='store_true', help='Fetch full descriptions')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--test', type=str, help='Test matcher with a title')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.test:
        test_matcher(args.test)
    else:
        run_console_scraper(max_pages=args.pages, fetch_descriptions=args.descriptions)


if __name__ == "__main__":
    main()
