"""CLI entry point for SS-Crawler."""
import sys
import argparse
from datetime import datetime
from typing import Optional

from src.scraper.engine import Scraper
from src.scraper.cpu_scraper import CPUScraper
from src.scraper.ssd_scraper import SSDScraper
from src.utils.config import AppConfig
from src.utils.logger import get_logger, setup_logging
from src.database.connection import init_database, get_session
from src.database.repository import GPUReferenceRepository, CPUReferenceRepository, SSDReferenceRepository, ScrapeRunRepository
from sqlalchemy import text

logger = get_logger("cli")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="ss-crawler",
        description="SS.com GPU and CPU scraper with intelligent matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape GPUs (default)
  %(prog)s scrape --gpu
  
  # Scrape CPUs
  %(prog)s scrape --cpu
  
  # Scrape both GPUs and CPUs
  %(prog)s scrape --gpu --cpu
  
  # Full scrape (5 pages default)
  %(prog)s scrape --gpu
  
  # Scrape unlimited pages
  %(prog)s scrape --cpu --max-pages 0
  
  # Scrape 10 pages
  %(prog)s scrape --gpu --max-pages 10
  
  # Limit to 50 listings total
  %(prog)s scrape --cpu --limit 50
  
  # Test mode
  %(prog)s scrape --gpu --test
  
  # Dry run - parse but don't save
  %(prog)s scrape --gpu --dry-run
  
  # Test single URL (GPU)
  %(prog)s test-url "https://www.ss.com/.../123.html" --gpu
  
  # Test single URL (CPU)
  %(prog)s test-url "https://www.ss.com/.../123.html" --cpu
  
  # View last run report
  %(prog)s report
  
  # Check database stats
  %(prog)s stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Run scraper")
    scrape_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Scrape GPU listings"
    )
    scrape_parser.add_argument(
        "--cpu",
        action="store_true",
        help="Scrape CPU listings"
    )
    scrape_parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test mode - fetch fewer listings"
    )
    scrape_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="Maximum listings to scrape (0 = unlimited)"
    )
    scrape_parser.add_argument(
        "--max-pages", "-p",
        type=int,
        default=5,
        help="Maximum pages to scrape (0 = unlimited, default: 5)"
    )
    scrape_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Parse only, don't save to database"
    )
    scrape_parser.add_argument(
        "--ssd",
        action="store_true",
        help="Scrape SSD listings"
    )
    scrape_parser.add_argument(
        "--confidence",
        type=float,
        default=0.70,
        help="Minimum confidence threshold for matches (0.0-1.0)"
    )
    
    # Test URL command
    test_parser = subparsers.add_parser("test-url", help="Test single URL parsing")
    test_parser.add_argument(
        "url",
        help="URL to test"
    )
    test_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Parse as GPU listing (default)"
    )
    test_parser.add_argument(
        "--cpu",
        action="store_true",
        help="Parse as CPU listing"
    )
    test_parser.add_argument(
        "--ssd",
        action="store_true",
        help="Parse as SSD listing"
    )
    test_parser.add_argument(
        "--save-html",
        action="store_true",
        help="Save HTML sample for debugging"
    )
    
    # Report command
    subparsers.add_parser("report", help="Show last scrape report")
    
    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Display current configuration"
    )
    config_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset to default configuration"
    )
    
    return parser


def cmd_scrape(args: argparse.Namespace) -> int:
    """Execute scrape command."""
    # If neither --gpu nor --cpu nor --ssd specified, default to GPU
    if not args.gpu and not args.cpu and not args.ssd:
        args.gpu = True
    
    exit_code = 0
    
    if args.gpu:
        exit_code = _scrape_gpu(args)
    
    if args.cpu:
        code = _scrape_cpu(args)
        if code != 0:
            exit_code = code
    
    if args.ssd:
        code = _scrape_ssd(args)
        if code != 0:
            exit_code = code
    
    return exit_code


def _scrape_gpu(args: argparse.Namespace) -> int:
    """Execute GPU scrape."""
    print("\n" + "=" * 50)
    print("Starting GPU Scraper...")
    print("=" * 50)
    
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
    
    config.scraper.min_confidence_threshold = args.confidence
    print(f"Confidence threshold: {args.confidence:.0%}")
    
    print("-" * 50)
    
    try:
        scraper = Scraper(config)
        stats = scraper.run()
        
        print("\n" + "=" * 50)
        print("GPU SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['total']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Unmatched:           {stats['unmatched']}")
        print(f"Low confidence:      {stats['low_confidence']}")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"\nGPU Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_cpu(args: argparse.Namespace) -> int:
    """Execute CPU scrape."""
    print("\n" + "=" * 50)
    print("Starting CPU Scraper...")
    print("=" * 50)
    
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
    
    config.scraper.min_confidence_threshold = args.confidence
    print(f"Confidence threshold: {args.confidence:.0%}")
    
    print("-" * 50)
    
    try:
        scraper = CPUScraper(config)
        stats = scraper.run()
        
        print("\n" + "=" * 50)
        print("CPU SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['total']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Unmatched:           {stats['unmatched']}")
        print(f"Low confidence:      {stats['low_confidence']}")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"\nCPU Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_ssd(args: argparse.Namespace) -> int:
    """Execute SSD scrape."""
    print("\n" + "=" * 50)
    print("Starting SSD Scraper...")
    print("=" * 50)
    
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
    
    config.scraper.min_confidence_threshold = args.confidence
    print(f"Confidence threshold: {args.confidence:.0%}")
    
    print("-" * 50)
    
    try:
        scraper = SSDScraper(config)
        listings = scraper.scrape_category(
            max_pages=args.max_pages,
            limit=args.limit
        )
        
        stats = scraper.get_stats()
        
        print("\n" + "=" * 50)
        print("SSD SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Matched:             {stats['matched']}")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"\nSSD Scrape Error: {e}", file=sys.stderr)
        return 1


def cmd_test_url(args: argparse.Namespace) -> int:
    """Execute test-url command."""
    # Default to GPU if none specified
    if not args.gpu and not args.cpu and not args.ssd:
        args.gpu = True
    
    if args.ssd:
        return _test_url_ssd(args)
    elif args.cpu:
        return _test_url_cpu(args)
    else:
        return _test_url_gpu(args)


def _test_url_gpu(args: argparse.Namespace) -> int:
    """Test single GPU URL."""
    from src.models.schemas import MatchResult
    
    print(f"Testing GPU URL: {args.url}")
    print("=" * 50)
    
    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html
    
    try:
        scraper = Scraper(config)
        scraper.initialize()
        
        listing, match = scraper.run_single(args.url)
        
        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            print(f"Title:       {listing.title}")
            if listing.price_eur > 0:
                print(f"Price:       EUR {listing.price_eur:.2f}")
            else:
                print("Price:       N/A")
            if listing.vram_mb:
                vram_gb = listing.vram_mb / 1024
                vram_note = f"{vram_gb:.1f} GB (site shows: {listing.vram_mb} MB)"
                if listing.vram_mb in [12288, 8192, 16384, 24576, 4096, 6144]:
                    raw_suspicious = [1200, 800, 1600, 2400, 400, 600, 1100, 1500, 2300, 700]
                    if any(abs(listing.vram_mb/10 - s) < 100 for s in raw_suspicious):
                        vram_note += " [AUTO-CORRECTED from typo]"
                print(f"VRAM:        {vram_note}")
            else:
                print("VRAM:        Not specified on site")
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Date:        {listing.date_posted}")
            
            if match.gpu:
                print("\nGPU MATCH:")
                print("-" * 50)
                print(f"Model:       {match.gpu.vendor} {match.gpu.model}")
                if match.gpu.vram_gb:
                    ref_vram_gb = match.gpu.vram_gb / 1024
                    print(f"VRAM:        {ref_vram_gb:.0f} GB (reference)")
                else:
                    print("VRAM:        N/A (reference)")
                print(f"Year:        {match.gpu.year_released or 'N/A'}")
                print(f"Confidence:  {match.confidence:.1%}")
                print(f"Method:      {match.method}")
                
                if listing.vram_mb and match.gpu.vram_gb:
                    vram_diff = abs(listing.vram_mb - match.gpu.vram_gb) / 1024
                    if vram_diff < 0.5:
                        print("VRAM Status: [OK] Matches reference (within 0.5 GB)")
                    elif vram_diff < 2:
                        print(f"VRAM Status: [WARN] Off by {vram_diff:.1f} GB")
                    else:
                        print(f"VRAM Status: [MISMATCH] Difference: {vram_diff:.1f} GB")
            else:
                print("\nNo GPU match found")
                print("\nTop candidates:")
                if scraper.matcher:
                    candidates = scraper.matcher.get_candidates(
                        listing.title,
                        limit=5,
                        vram_mb=listing.vram_mb
                    )
                    for gpu, score in candidates:
                        vram_info = f"{gpu.vram_gb/1024:.0f} GB" if gpu.vram_gb else "N/A"
                        print(f"  - {gpu.vendor} {gpu.model} ({vram_info}) - score: {score:.1%}")
            
            if args.save_html:
                print(f"\nHTML saved to logs/html_samples/")
            
            return 0
        else:
            print("Failed to parse listing")
            return 1
            
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def _test_url_cpu(args: argparse.Namespace) -> int:
    """Test single CPU URL."""
    from src.models.schemas import CPUMatchResult
    
    print(f"Testing CPU URL: {args.url}")
    print("=" * 50)
    
    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html
    
    try:
        scraper = CPUScraper(config)
        scraper.initialize()
        
        listing, match = scraper.run_single(args.url)
        
        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            try:
                print(f"Title:       {listing.title}")
            except UnicodeEncodeError:
                print(f"Title:       {listing.title.encode('utf-8', 'ignore').decode()}")
            if listing.price_eur > 0:
                print(f"Price:       EUR {listing.price_eur:.2f}")
            else:
                print("Price:       N/A")
            print(f"Category:    {listing.category}")
            try:
                print(f"Location:    {listing.seller_location or 'N/A'}")
            except UnicodeEncodeError:
                print(f"Location:    {(listing.seller_location or 'N/A').encode('utf-8', 'ignore').decode()}")
            print(f"Date:        {listing.date_posted}")
            
            if match.cpu:
                print("\nCPU MATCH:")
                print("-" * 50)
                print(f"Producer:    {match.cpu.producer}")
                try:
                    print(f"Name:        {match.cpu.cpu_name}")
                except UnicodeEncodeError:
                    print(f"Name:        {match.cpu.cpu_name.encode('utf-8', 'ignore').decode()}")
                print(f"Processor:   {match.cpu.processor_number}")
                if match.cpu.cores:
                    print(f"Cores:       {match.cpu.cores}")
                if match.cpu.threads:
                    print(f"Threads:     {match.cpu.threads}")
                if match.cpu.socket:
                    print(f"Socket:      {match.cpu.socket}")
                print(f"Confidence:  {match.confidence:.1%}")
                print(f"Method:      {match.method}")
            else:
                print("\nNo CPU match found")
                print("\nTop candidates:")
                if scraper.matcher:
                    candidates = scraper.matcher.get_candidates(
                        listing.title,
                        limit=5
                    )
                    for cpu, score in candidates:
                        try:
                            print(f"  - {cpu.producer} {cpu.cpu_name} ({cpu.processor_number}) - score: {score:.1%}")
                        except UnicodeEncodeError:
                            name = cpu.cpu_name.encode('utf-8', 'ignore').decode()
                            print(f"  - {cpu.producer} {name} ({cpu.processor_number}) - score: {score:.1%}")
            
            if args.save_html:
                print(f"\nHTML saved to logs/html_samples/")
            
            return 0
        else:
            print("Failed to parse listing")
            return 1
            
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def _test_url_ssd(args: argparse.Namespace) -> int:
    """Test single SSD URL."""
    from src.models.schemas import SSDMatchResult
    
    print(f"Testing SSD URL: {args.url}")
    print("=" * 50)
    
    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html
    
    try:
        scraper = SSDScraper(config)
        scraper.initialize()
        
        listing = scraper.scrape_single(args.url)
        
        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            print(f"Title:       {listing.title}")
            if listing.price_eur > 0:
                print(f"Price:       EUR {listing.price_eur:.2f}")
            else:
                print("Price:       N/A")
            if listing.capacity_gb:
                print(f"Capacity:    {listing.capacity_gb} GB")
            else:
                print("Capacity:    Not specified")
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Category:    {listing.category}")
            
            if listing.matched_ssd_id:
                print("\nSSD MATCH:")
                print("-" * 50)
                ssd = scraper.matcher.get_ssd_by_id(listing.matched_ssd_id)
                if ssd:
                    print(f"Brand:       {ssd.brand}")
                    print(f"Model:       {ssd.model}")
                    if ssd.capacity_gb:
                        print(f"Capacity:    {ssd.capacity_gb} GB")
                    print(f"Interface:   {ssd.interface or 'N/A'}")
                    print(f"Form Factor: {ssd.form_factor or 'N/A'}")
                    print(f"Confidence:  {listing.ssd_confidence_score:.1%}")
                    print(f"Method:      {listing.ssd_match_method}")
            else:
                print("\nNo SSD match found")
            
            if args.save_html:
                print(f"\nHTML saved to logs/html_samples/")
            
            return 0
        else:
            print("Failed to parse listing")
            return 1
            
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    """Execute report command."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Get last run
        result = session.execute(text("""
            SELECT * FROM scrape_runs
            ORDER BY started_at DESC
            LIMIT 1
        """)).fetchone()
        
        if not result:
            print("No scrape runs found.")
            return 0
        
        run = dict(result._mapping)
        
        print("LAST SCRAPE REPORT")
        print("=" * 50)
        print(f"Run ID:      {run['id']}")
        print(f"Started:     {run['started_at']}")
        print(f"Completed:   {run['completed_at'] or 'N/A'}")
        print(f"Status:      {run['status'].upper()}")
        print(f"Category:    {run['category'] or 'N/A'}")
        print("-" * 50)
        print(f"Total:       {run['total_listings']}")
        print(f"New:         {run['new_listings']}")
        print(f"Updated:     {run['updated_listings']}")
        print(f"Skipped:     {run['skipped_unchanged']}")
        print(f"Failed:      {run['failed_requests']}")
        
        if run['error_message']:
            print("-" * 50)
            print(f"Error: {run['error_message']}")
        
        return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Execute stats command."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    with get_session() as session:
        # Get counts
        listings_total = session.execute(text("SELECT COUNT(*) FROM listings")).scalar()
        listings_active = session.execute(text("SELECT COUNT(*) FROM listings WHERE is_active = true")).scalar()
        listings_unmatched = session.execute(text("SELECT COUNT(*) FROM listings WHERE matched_gpu_id IS NULL AND matched_cpu_id IS NULL AND matched_ssd_id IS NULL")).scalar()
        
        gpu_count = session.execute(text("SELECT COUNT(*) FROM gpu_reference")).scalar()
        cpu_count = session.execute(text("SELECT COUNT(*) FROM cpu_reference")).scalar()
        ssd_count = session.execute(text("SELECT COUNT(*) FROM ssd_reference")).scalar()
        
        gpu_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'gpu'")).scalar()
        cpu_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'cpu'")).scalar()
        ssd_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'ssd'")).scalar()
        
        price_entries = session.execute(text("SELECT COUNT(*) FROM price_history")).scalar()
        
        print("DATABASE STATISTICS")
        print("=" * 50)
        print(f"GPU References:        {gpu_count}")
        print(f"CPU References:        {cpu_count}")
        print(f"SSD References:        {ssd_count}")
        print(f"Total Listings:        {listings_total}")
        print(f"  - GPU Listings:      {gpu_listings}")
        print(f"  - CPU Listings:      {cpu_listings}")
        print(f"  - SSD Listings:      {ssd_listings}")
        print(f"  - Active:            {listings_active}")
        print(f"  - Inactive:          {listings_total - listings_active}")
        print(f"  - Unmatched:         {listings_unmatched}")
        print(f"Price History Entries: {price_entries}")
        
        # Top GPUs by listing count
        print("\nTOP GPUs BY LISTINGS:")
        print("-" * 50)
        top_gpus = session.execute(text("""
            SELECT g.vendor, g.model, g.vram_gb, COUNT(*) as cnt
            FROM listings l
            JOIN gpu_reference g ON l.matched_gpu_id = g.id
            WHERE l.is_active = true AND l.category = 'gpu'
            GROUP BY g.id, g.vendor, g.model, g.vram_gb
            ORDER BY cnt DESC
            LIMIT 5
        """)).fetchall()
        
        for gpu in top_gpus:
            vram_str = f" ({gpu['vram_gb']}GB)" if gpu['vram_gb'] else ""
            print(f"  {gpu['vendor']} {gpu['model']}{vram_str}: {gpu['cnt']} listings")
        
        # Top CPUs by listing count
        print("\nTOP CPUs BY LISTINGS:")
        print("-" * 50)
        top_cpus = session.execute(text("""
            SELECT c.producer, c.cpu_name, c.cores, COUNT(*) as cnt
            FROM listings l
            JOIN cpu_reference c ON l.matched_cpu_id = c.id
            WHERE l.is_active = true AND l.category = 'cpu'
            GROUP BY c.id, c.producer, c.cpu_name, c.cores
            ORDER BY cnt DESC
            LIMIT 5
        """)).fetchall()
        
        for cpu in top_cpus:
            cores_str = f" ({cpu['cores']} cores)" if cpu['cores'] else ""
            print(f"  {cpu['producer']} {cpu['cpu_name']}{cores_str}: {cpu['cnt']} listings")
        
        return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Execute config command."""
    if args.reset:
        config = AppConfig()
        config.save()
        print("Configuration reset to defaults")
        return 0
    
    if args.show or True:  # Default to show
        config = AppConfig.from_yaml()
        
        print("CURRENT CONFIGURATION")
        print("=" * 50)
        print(f"Scraper:")
        print(f"  Base URL:    {config.scraper.base_url}")
        print(f"  GPU Path:    {config.scraper.category_path}")
        print(f"  CPU Path:    /lv/electronics/computers/completing-pc/cpu/")
        print(f"  Test Mode:   {config.scraper.test_mode}")
        print(f"  Max Items:   {config.scraper.max_listings or 'unlimited'}")
        print(f"  Confidence:  {config.scraper.min_confidence_threshold:.0%}")
        print(f"\nDatabase:")
        print(f"  Host:        {config.database.host}:{config.database.port}")
        print(f"  Database:    {config.database.name}")
        print(f"  User:        {config.database.user}")
        print(f"\nLogging:")
        print(f"  Level:       {config.logging.level}")
        print(f"  File:        {config.logging.file}")
        print(f"  Console:     {config.logging.console}")
        
        return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 0
    
    commands = {
        'scrape': cmd_scrape,
        'test-url': cmd_test_url,
        'report': cmd_report,
        'stats': cmd_stats,
        'config': cmd_config,
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    
    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
