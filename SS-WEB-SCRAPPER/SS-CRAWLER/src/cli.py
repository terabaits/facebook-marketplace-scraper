"""CLI entry point for SS-Crawler."""
import sys
import argparse
from datetime import datetime
from typing import Optional

from src.scraper.engine import Scraper
from src.scraper.cpu_scraper import CPUScraper
from src.scraper.ssd_scraper import SSDScraper
from src.scraper.ram_scraper import RAMScraper
from src.scraper.motherboard_scraper import MotherboardScraper
from src.scraper.monitor_scraper import MonitorScraper
from src.scraper.console_scraper import ConsoleScraper
from src.scraper.lens_scraper import LensScraper
from src.scraper.camera_scraper import CameraScraper
from src.scraper.computer_scraper import ComputerScraper
from src.scraper.laptop_scraper import LaptopScraper
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

  # Scrape RAM
  %(prog)s scrape --ram

  # Scrape everything
  %(prog)s scrape --gpu --cpu --ssd --ram

  # Full scrape (5 pages default, laptops default 25)
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
        help="Maximum pages to scrape (0 = unlimited, default: 5; laptops default to 25)"
    )
    scrape_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Parse only, don't save to database"
    )
    scrape_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip database backup before scrape"
    )
    scrape_parser.add_argument(
        "--ssd",
        action="store_true",
        help="Scrape SSD listings"
    )
    scrape_parser.add_argument(
        "--ram",
        action="store_true",
        help="Scrape RAM listings"
    )
    scrape_parser.add_argument(
        "--cases",
        action="store_true",
        help="Scrape Cases listings"
    )
    scrape_parser.add_argument(
        "--psu",
        action="store_true",
        help="Scrape PSU listings"
    )
    scrape_parser.add_argument(
        "--confidence",
        type=float,
        default=0.70,
        help="Minimum confidence threshold for matches (0.0-1.0)"
    )
    scrape_parser.add_argument(
        "--motherboards",
        action="store_true",
        help="Scrape Motherboard listings"
    )
    scrape_parser.add_argument(
        "--monitors",
        action="store_true",
        help="Scrape Monitor listings"
    )
    scrape_parser.add_argument(
        "--consoles",
        action="store_true",
        help="Scrape Console listings"
    )
    scrape_parser.add_argument(
        "--lenses",
        action="store_true",
        help="Scrape Camera Lens listings"
    )
    scrape_parser.add_argument(
        "--cameras",
        action="store_true",
        help="Scrape Camera Body listings"
    )
    scrape_parser.add_argument(
        "--computers",
        action="store_true",
        help="Scrape complete computer listings"
    )
    scrape_parser.add_argument(
        "--laptops",
        action="store_true",
        help="Scrape Laptop listings"
    )
    scrape_parser.add_argument(
        "--andele",
        action="store_true",
        help="Use Andele Mandele scraper instead of SS.com"
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
        "--ram",
        action="store_true",
        help="Parse as RAM listing"
    )
    test_parser.add_argument(
        "--cases",
        action="store_true",
        help="Parse as Case listing"
    )
    test_parser.add_argument(
        "--psu",
        action="store_true",
        help="Parse as PSU listing"
    )
    test_parser.add_argument(
        "--motherboards",
        action="store_true",
        help="Parse as Motherboard listing"
    )
    test_parser.add_argument(
        "--monitors",
        action="store_true",
        help="Parse as Monitor listing"
    )
    test_parser.add_argument(
        "--consoles",
        action="store_true",
        help="Parse as Console listing"
    )
    test_parser.add_argument(
        "--lenses",
        action="store_true",
        help="Parse as Lens listing"
    )
    test_parser.add_argument(
        "--cameras",
        action="store_true",
        help="Parse as Camera Body listing"
    )
    test_parser.add_argument(
        "--computers",
        action="store_true",
        help="Parse as complete Computer listing"
    )
    test_parser.add_argument(
        "--laptops",
        action="store_true",
        help="Parse as Laptop listing"
    )
    test_parser.add_argument(
        "--andele",
        action="store_true",
        help="Parse as Andele Mandele listing"
    )
    test_parser.add_argument(
        "--save",
        action="store_true",
        help="Save parsed listing to database"
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
    import subprocess
    from datetime import datetime
    from src.utils.config import AppConfig

    # Load config for database credentials
    config = AppConfig.from_yaml()

    # Backup database before scrape (unless --no-backup)
    if not getattr(args, 'no_backup', False):
        backup_file = f"backup_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.sql"
        backup_path = f"G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER\\{backup_file}"

        print(f"\nCreating database backup: {backup_file}")
        try:
            # Find pg_dump executable - prefer newer versions
            pg_dump_paths = [
                r'C:\Program Files\PostgreSQL\15\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\14\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\13\bin\pg_dump.exe',
                'pg_dump'
            ]

            pg_dump_exe = None
            import os
            for path in pg_dump_paths:
                if os.path.exists(path):
                    pg_dump_exe = path
                    break

            if not pg_dump_exe:
                raise FileNotFoundError("pg_dump.exe not found. Install PostgreSQL 15+ or use --no-backup")

            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = config.database.password

            result = subprocess.run(
                [pg_dump_exe, '-h', 'localhost', '-p', '5433', '-U', 'crawler', 'ss_market'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                env=env
            )
            if result.returncode == 0:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                print(f"✅ Backup saved: {backup_path}")
            else:
                print(f"⚠️ Backup failed: {result.stderr}")
                print("Continue anyway? (y/n)")
                response = input().lower()
                if response != 'y':
                    return 1
        except Exception as e:
            print(f"⚠️ Could not create backup: {e}")
            print("Continue anyway? (y/n)")
            response = input().lower()
            if response != 'y':
                return 1

    # If neither --gpu nor --cpu nor --ssd nor --ram specified, default to GPU
    if not args.gpu and not args.cpu and not args.ssd and not args.ram and not args.cases and not args.psu and not args.motherboards and not args.monitors and not args.consoles and not args.lenses and not args.cameras and not args.computers and not args.laptops:
        args.gpu = True

    # Handle Andele scraper
    if args.andele:
        return _scrape_andele(args)

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

    if args.ram:
        code = _scrape_ram(args)
        if code != 0:
            exit_code = code

    if args.cases:
        code = _scrape_cases(args)
        if code != 0:
            exit_code = code

    if args.psu:
        code = _scrape_psu(args)
        if code != 0:
            exit_code = code

    if args.motherboards:
        code = _scrape_motherboards(args)
        if code != 0:
            exit_code = code

    if args.monitors:
        code = _scrape_monitors(args)
        if code != 0:
            exit_code = code

    if args.consoles:
        code = _scrape_consoles(args)
        if code != 0:
            exit_code = code

    if args.lenses:
        code = _scrape_lenses(args)
        if code != 0:
            exit_code = code

    if args.cameras:
        code = _scrape_cameras(args)
        if code != 0:
            exit_code = code

    if args.computers:
        code = _scrape_computers(args)
        if code != 0:
            exit_code = code

    if args.laptops:
        code = _scrape_laptops(args)
        if code != 0:
            exit_code = code

    return exit_code


def _scrape_andele(args: argparse.Namespace) -> int:
    """Execute Andele Mandele scrape."""

    print("\n" + "=" * 50)
    print("Starting Andele Mandele Scraper...")
    print("=" * 50)

    if args.dry_run:
        print("DRY RUN - will not save to database")

    print("-" * 50)

    # Determine categories to scrape
    categories = []
    if args.gpu:
        categories.append('gpu')
    if args.cpu:
        categories.append('cpu')
    if args.ssd:
        categories.append('ssd')
    if args.ram:
        categories.append('ram')
    if args.psu:
        categories.append('psu')
    if args.monitors:
        categories.append('monitor')
    if args.motherboards:
        categories.append('motherboard')
    if args.computers:
        categories.append('computer')

    # If no category specified, scrape GPU by default
    if not categories:
        categories = ['gpu']
        print("No category specified, defaulting to GPU")

    print(f"Categories: {', '.join(categories)}")
    print(f"Max pages: {args.max_pages if args.max_pages > 0 else 'unlimited'}")
    print(f"Limit: {args.limit if args.limit > 0 else 'unlimited'}")
    print("-" * 50)

    total_stats = {
        'total': 0,
        'new': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0,
    }

    try:
        # Handle computers specially with dedicated scraper
        if 'computer' in categories:
            categories.remove('computer')
            print("\n📂 Using AndeleComputerScraper for COMPUTERS...")
            from src.scraper.andele_computer_scraper import AndeleComputerScraper
            comp_scraper = AndeleComputerScraper(dry_run=args.dry_run)
            comp_result = comp_scraper.scrape_computers(args.max_pages, args.limit)

            total_stats['total'] += comp_result.total
            total_stats['new'] += comp_result.new
            total_stats['updated'] += comp_result.updated
            total_stats['failed'] += comp_result.failed
            total_stats['skipped'] += comp_result.skipped

        # Process remaining categories with regular scraper
        if categories:
            from src.scraper.andele_scraper import AndeleScraper
            scraper = AndeleScraper(dry_run=args.dry_run)

            for category in categories:
                print(f"\n📂 Scraping {category.upper()}...")
                result = scraper.scrape_category(category, args.max_pages, args.limit)

                total_stats['total'] += result.total
                total_stats['new'] += result.new
                total_stats['updated'] += result.updated
                total_stats['failed'] += result.failed
                total_stats['skipped'] += result.skipped

        print("\n" + "=" * 50)
        print("ANDELE SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {total_stats['total']}")
        print(f"New listings:        {total_stats['new']}")
        print(f"Updated:             {total_stats['updated']}")
        print(f"Skipped:             {total_stats['skipped']}")
        print(f"Failed:              {total_stats['failed']}")
        print("=" * 50)

        if result.errors:
            print(f"\n⚠️  Errors ({len(result.errors)}):")
            for error in result.errors[:5]:
                print(f"  - {error[:80]}...")

        return 0

    except Exception as e:
        print(f"\n❌ Andele Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


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


def _scrape_ram(args: argparse.Namespace) -> int:
    """Execute RAM scrape."""
    print("\n" + "=" * 50)
    print("Starting RAM Scraper...")
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
        scraper = RAMScraper(config)
        listings = scraper.scrape_category(
            max_pages=args.max_pages,
            limit=args.limit
        )

        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("RAM SCRAPE SUMMARY")
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
        print(f"\nRAM Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_cases(args: argparse.Namespace) -> int:
    """Execute Cases scrape."""
    print("\n" + "=" * 50)
    print("Starting Cases Scraper...")
    print("=" * 50)

    config = AppConfig.from_yaml()

    # Set cases category path
    config.scraper.category_path = "/lv/electronics/computers/completing-pc/cases/"

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
        from src.scraper.cases_scraper import CasesScraper
        from src.scraper.crawler import Crawler
        from src.database.connection import init_database

        # Initialize database first
        init_database(config.database)

        crawler = Crawler(config.scraper)
        scraper = CasesScraper(config, crawler)

        listings = scraper.scrape_category()

        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("CASES SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Matched:             {stats['matched']}")
        print(f"Cases:               {stats['cases']}")
        print(f"PSUs:                {stats['psus']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nCases Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_psu(args: argparse.Namespace) -> int:
    """Execute PSU scrape (same as cases but filtered)."""
    print("\n" + "=" * 50)
    print("Starting PSU Scraper...")
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
        from src.scraper.cases_scraper import CasesScraper
        from src.scraper.crawler import Crawler

        crawler = Crawler(config.scraper)
        scraper = CasesScraper(config, crawler)

        listings = scraper.scrape_category()

        # Filter to PSUs only for stats
        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("PSU SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Matched:             {stats['matched']}")
        print(f"PSUs:                {stats['psus']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nPSU Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_motherboards(args: argparse.Namespace) -> int:
    """Execute Motherboard scrape."""
    print("\n" + "=" * 50)
    print("Starting Motherboard Scraper...")
    print("=" * 50)

    config = AppConfig.from_yaml()

    if args.test:
        config.scraper.test_mode = True
        print("TEST MODE ENABLED")

    if args.limit > 0:
        config.scraper.max_listings = args.limit
        print(f"Limit: {args.limit} listings")

    # Motherboards default to 3 pages unless explicitly overridden
    max_pages = args.max_pages if args.max_pages != 5 else 3
    if max_pages >= 0:
        config.scraper.max_pages = max_pages
        if max_pages == 0:
            print("Pages: unlimited")
        else:
            print(f"Pages: {max_pages}")

    if args.dry_run:
        print("DRY RUN - will not save to database")

    config.scraper.min_confidence_threshold = args.confidence
    print(f"Confidence threshold: {args.confidence:.0%}")

    print("-" * 50)

    try:
        scraper = MotherboardScraper(config)
        listings = scraper.scrape_category(
            max_pages=max_pages,
            limit=args.limit
        )

        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("MOTHERBOARD SCRAPE SUMMARY")
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
        print(f"\nMotherboard Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_monitors(args: argparse.Namespace) -> int:
    """Execute Monitor scrape."""
    print("\n" + "=" * 50)
    print("Starting Monitor Scraper...")
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
        scraper = MonitorScraper(config)
        listings = scraper.scrape_category(
            max_pages=args.max_pages,
            limit=args.limit
        )

        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("MONITOR SCRAPE SUMMARY")
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
        print(f"\nMonitor Scrape Error: {e}", file=sys.stderr)
        return 1


def _scrape_consoles(args: argparse.Namespace) -> int:
    """Execute Console scrape."""
    print("\n" + "=" * 50)
    print("Starting Console Scraper...")
    print("=" * 50)

    config = AppConfig.from_yaml()

    # Set console category path
    config.scraper.category_path = "/lv/electronics/computers/game-consoles/"

    if args.test:
        config.scraper.test_mode = True
        print("TEST MODE ENABLED")

    # If limit is specified but max_pages is default (5), set pages to unlimited
    # The scraper will stop when it reaches the listing limit
    if args.limit > 0 and args.max_pages == 5:
        config.scraper.max_pages = 0  # Unlimited
        print(f"Limit: {args.limit} listings (from page 1 only)")
    elif args.limit > 0:
        config.scraper.max_listings = args.limit
        print(f"Limit: {args.limit} listings")

    if args.max_pages >= 0 and args.limit == 0:
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
        from src.database.connection import init_database
        from src.scraper.crawler import Crawler
        from src.scraper.console_scraper import ConsoleScraper

        # Initialize database first
        init_database(config.database)

        crawler = Crawler(config.scraper)
        scraper = ConsoleScraper(config, crawler)

        listings = scraper.scrape_category(max_pages=args.max_pages, limit=args.limit)

        # Process listings through matcher and save to database
        from src.database.console_repository import ConsoleRepository
        from src.database.repository import ListingRepository
        from src.scraper.console_matcher import ConsoleMatcher
        from src.database.connection import get_session

        # Load matcher data
        repo = ConsoleRepository()
        repo.load_references()
        consoles = repo.consoles
        variants = repo.variants
        editions = repo.editions

        matcher = ConsoleMatcher(consoles, variants, editions)

        processed = 0
        new_count = 0
        updated_count = 0
        matched_count = 0

        for raw_listing in listings[:args.limit if args.limit > 0 else None]:
            try:
                # Match console
                match_result = matcher.match(
                    raw_listing['title'],
                    "",  # Description will be fetched later
                    price=raw_listing['price_eur']
                )

                # Show match result
                if match_result.console:
                    matched_count += 1
                    console_name = match_result.console.name
                    confidence = match_result.console_confidence
                    method = match_result.method
                    print(f"  ✓ MATCHED: {console_name} ({confidence:.0%} confidence) - {method}")
                    print(f"    URL: {raw_listing['listing_url']}")
                    if match_result.variant:
                        print(f"    Variant: {match_result.variant.model_name}")
                else:
                    print(f"  ✗ NO MATCH: {raw_listing['title'][:60]}...")
                    print(f"    URL: {raw_listing['listing_url']}")

                if not args.dry_run:
                    # Save to database using ConsoleRepository
                    from src.models.schemas import ConsoleListing

                    listing = ConsoleListing(
                        listing_id=raw_listing['listing_id'],
                        title=raw_listing['title'],
                        description="",
                        price_eur=raw_listing['price_eur'],
                        seller_location=raw_listing.get('seller_location'),
                        listing_url=raw_listing['listing_url'],
                        matched_console_id=match_result.console.id if match_result.console else None,
                        matched_variant_id=match_result.variant.id if match_result.variant else None,
                        matched_edition_id=match_result.edition.id if match_result.edition else None,
                        console_confidence_score=match_result.console_confidence,
                        variant_confidence_score=match_result.variant_confidence,
                        edition_confidence_score=match_result.edition_confidence,
                        console_match_method=match_result.method
                    )

                    success = repo.save_listing(listing, match_result)

                    if success:
                        new_count += 1

                processed += 1

            except Exception as e:
                logger.error(f"Error processing listing {raw_listing.get('listing_id')}: {e}")
                continue

        stats = {
            'processed': processed,
            'new': new_count,
            'updated': updated_count,
            'matched': matched_count
        }

        print("\n" + "=" * 50)
        print("CONSOLE SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats.get('processed', len(listings))}")
        print(f"New listings:        {stats.get('new', 0)}")
        print(f"Price updates:       {stats.get('updated', 0)}")
        print(f"Unchanged:           {stats.get('unchanged', 0)}")
        print(f"Failed:              {stats.get('failed', 0)}")
        print(f"Matched:             {stats.get('matched', 0)}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nConsole Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _scrape_lenses(args: argparse.Namespace) -> int:
    """Execute Lens scrape."""
    print("\n" + "=" * 50)
    print("Starting Lens Scraper...")
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
        scraper = LensScraper(config)
        listings = scraper.scrape_category(
            max_pages=args.max_pages,
            limit=args.limit
        )

        # Save listings to database
        if not args.dry_run:
            from src.database.connection import get_session
            from src.database.repository import ListingRepository

            with get_session() as session:
                new_count = 0
                updated_count = 0

                for listing in listings:
                    try:
                        action = ListingRepository.create_or_update(session, listing, None)
                        if action == 'new':
                            new_count += 1
                        elif action == 'updated':
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"Error saving listing {listing.listing_id}: {e}")
                        continue

                session.commit()

                # Update stats with actual save counts
                stats = scraper.get_stats()
                stats['new'] = new_count
                stats['updated'] = updated_count
        else:
            stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("LENS SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Updated:             {stats['updated']}")
        print(f"Filtered:            {stats['filtered']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Matched:             {stats['matched']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nLens Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _scrape_cameras(args: argparse.Namespace) -> int:
    """Execute Camera Body scrape."""
    print("\n" + "=" * 50)
    print("Starting Camera Body Scraper...")
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
        scraper = CameraScraper(config)
        listings = scraper.scrape_category(
            max_pages=args.max_pages,
            limit=args.limit
        )

        # Save listings to database
        if not args.dry_run:
            from src.database.connection import get_session
            from src.database.repository import ListingRepository

            with get_session() as session:
                new_count = 0
                updated_count = 0

                for listing in listings:
                    try:
                        action = ListingRepository.create_or_update(session, listing, None)
                        if action == 'new':
                            new_count += 1
                        elif action == 'updated':
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"Error saving listing {listing.listing_id}: {e}")
                        continue

                session.commit()

                # Update stats with actual save counts
                stats = scraper.get_stats()
                stats['new'] = new_count
                stats['updated'] = updated_count
        else:
            stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("CAMERA SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Updated:             {stats['updated']}")
        print(f"Matched unchanged:   {stats.get('matched_unchanged', 0)}")
        print(f"Passed filter, unmatched: {stats.get('passed_filter_unmatched', 0)}")
        print(f"Filtered:            {stats['filtered']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Matched:             {stats['matched']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nCamera Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _scrape_laptops(args: argparse.Namespace) -> int:
    """Execute Laptop scrape."""
    print("\n" + "=" * 50)
    print("Starting Laptop Scraper...")
    print("=" * 50)

    config = AppConfig.from_yaml()

    if args.test:
        config.scraper.test_mode = True
        print("TEST MODE ENABLED")

    if args.limit > 0:
        config.scraper.max_listings = args.limit
        print(f"Limit: {args.limit} listings")

    # Laptop category default to 5 pages unless the user explicitly overrides --max-pages.
    max_pages = args.max_pages

    if max_pages >= 0:
        config.scraper.max_pages = max_pages
        if max_pages == 0:
            print("Pages: unlimited")
        else:
            print(f"Pages: {max_pages}")

    if args.dry_run:
        print("DRY RUN - will not save to database")

    print("-" * 50)

    try:
        from src.database.connection import init_database
        from src.scraper.crawler import Crawler
        from src.scraper.laptop_scraper import LaptopScraper

        # Initialize database first
        init_database(config.database)

        crawler = Crawler(config.scraper)
        scraper = LaptopScraper(config, crawler)

        listings = scraper.scrape_category(
            max_pages=max_pages,
            limit=args.limit
        )

        stats = scraper.get_stats()

        print("\n" + "=" * 50)
        print("LAPTOP SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['processed']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nLaptop Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_test_url(args: argparse.Namespace) -> int:
    """Execute test-url command."""
    # Handle Andele URLs
    if args.andele:
        return _test_url_andele(args)

    # Default to GPU if none specified
    if not args.gpu and not args.cpu and not args.ssd and not args.ram and not args.cases and not args.psu and not args.motherboards and not args.monitors and not args.consoles and not args.lenses and not args.cameras and not args.computers:
        args.gpu = True

    if args.computers:
        return _test_url_computers(args)
    elif args.laptops:
        return _test_url_laptops(args)
    elif args.cameras:
        return _test_url_camera(args)
    elif args.lenses:
        return _test_url_lens(args)
    elif args.ram:
        return _test_url_ram(args)
    elif args.cases or args.psu:
        return _test_url_cases(args)
    elif args.motherboards:
        return _test_url_motherboard(args)
    elif args.monitors:
        return _test_url_monitor(args)
    elif args.consoles:
        return _test_url_console(args)
    elif args.ssd:
        return _test_url_ssd(args)
    elif args.cpu:
        return _test_url_cpu(args)
    else:
        return _test_url_gpu(args)


def _test_url_cases(args: argparse.Namespace) -> int:
    """Test single Cases/PSU URL."""
    print(f"Testing Cases/PSU URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        from src.database.connection import init_database, get_session
        from src.scraper.crawler import Crawler, ErrorType
        from src.database.repository import CaseRepository, PSURepository

        # Initialize database
        init_database(config.database)
        from bs4 import BeautifulSoup
        import re

        crawler = Crawler(config.scraper)

        # Load matchers
        with get_session() as session:
            cases = CaseRepository.get_all(session)
            psus = PSURepository.get_all(session)

        # Fetch and parse
        result = crawler.fetch(args.url)

        if result.error_type != ErrorType.SUCCESS:
            print(f"Failed to fetch: {result.error_msg}")
            return 1

        # Extract listing ID from URL
        match = re.search(r'/([a-z]+)\.html$', args.url)
        if not match:
            print("Could not extract listing ID from URL")
            return 1

        listing_id = match.group(1)

        # Parse with BeautifulSoup
        soup = BeautifulSoup(result.html, 'html.parser')

        # Extract title
        title_elem = soup.find('title')
        title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""

        # Extract description
        msg_div = soup.find('div', {'id': 'msg_div_msg'})
        description = ""
        if msg_div:
            description = msg_div.get_text(separator=' ', strip=True)

        # Extract price
        price = 0.0
        price_cell = soup.find('td', {'class': 'ads_price'})
        if price_cell:
            price_text = price_cell.get_text(strip=True)
            price_match = re.search(r'([\d,]+)', price_text.replace(' ', ''))
            if price_match:
                price_str = price_match.group(1).replace(',', '.')
                try:
                    price = float(price_str)
                except ValueError:
                    pass

        # Extract location - look for "Vieta:" (Location) label
        location = ""
        for row in soup.find_all('tr'):
            label = row.find('td', {'class': 'ads_contacts_name'})
            if label and 'vieta' in label.get_text(strip=True).lower():
                value_cell = row.find('td', {'class': 'ads_contacts'})
                if value_cell:
                    # Get text but filter out phone number UI elements
                    full_text = value_cell.get_text(strip=True)
                    # Remove phone number text like "(+371)24-85-***Parādīt tālruni"
                    # Split by newlines and take only the first line (the actual location)
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    for line in lines:
                        # Skip lines that look like phone numbers or contain "tālruni" (phone)
                        if not re.search(r'\(\+\d+\)|tālruni|Parādīt', line, re.IGNORECASE):
                            location = line
                            break
                    break

        # Fallback to old methods
        if not location:
            address = soup.find('td', {'class': 'td_address'})
            if address:
                location = address.get_text(strip=True)

        listing = {
            'listing_id': listing_id,
            'title': title,
            'description': description,
            'price': price,
            'location': location,
            'url': args.url
        }

        # Categorize
        text_lower = (title + ' ' + description).lower()
        category = 'case' if any(k in text_lower for k in ['korpusu', 'case', 'korpuss']) else 'psu'
        listing['category'] = category

        # Match
        from src.scraper.case_matcher import CaseMatcher
        from src.scraper.psu_matcher import PSUMatcher

        if category == 'case':
            matcher = CaseMatcher(cases)
            match_result = matcher.match_listing(
                title + ' ' + description,
                price
            )
            if match_result.case:
                listing['matched_case_id'] = match_result.case.id
                listing['confidence_score'] = match_result.confidence
                listing['match_method'] = match_result.method
        else:
            matcher = PSUMatcher(psus)
            match_result = matcher.match_listing(
                title + ' ' + description,
                price
            )
            if match_result.psu:
                listing['matched_psu_id'] = match_result.psu.id
                listing['confidence_score'] = match_result.confidence
                listing['match_method'] = match_result.method

        # Output
        print("\nLISTING DATA:")
        print("-" * 50)
        print(f"ID:          {listing['listing_id']}")
        print(f"Title:       {listing['title']}")
        print(f"Price:       EUR {listing['price']:.2f}" if listing['price'] > 0 else "Price:       N/A")
        print(f"Location:    {listing.get('location', 'N/A')}")
        print(f"Category:    {category.upper()}")

        if category == 'case' and listing.get('matched_case_id'):
            print("\nCASE MATCH:")
            print("-" * 50)
            case = next((c for c in cases if c.id == listing['matched_case_id']), None)
            if case:
                print(f"Name:        {case.name}")
                print(f"Type:        {case.type or 'N/A'}")
                print(f"Form Factor: {case.form_factor or 'N/A'}")
                print(f"Confidence:  {listing['confidence_score']:.1%}")
                print(f"Method:      {listing['match_method']}")
        elif category == 'psu' and listing.get('matched_psu_id'):
            print("\nPSU MATCH:")
            print("-" * 50)
            psu = next((p for p in psus if p.id == listing['matched_psu_id']), None)
            if psu:
                print(f"Name:        {psu.name}")
                print(f"Wattage:     {psu.wattage or 'N/A'}W")
                print(f"Efficiency:  {psu.efficiency_rating or 'N/A'}")
                print(f"Modular:     {psu.modular or 'N/A'}")
                print(f"Confidence:  {listing['confidence_score']:.1%}")
                print(f"Method:      {listing['match_method']}")
        else:
            print("\nNo match found")

        # Save to database if --save flag
        if getattr(args, 'save', False):
            print("\n" + "-" * 50)
            try:
                from src.database.repository import ListingRepository
                from src.utils.text import compute_content_hash

                # Create listing object
                content_hash = compute_content_hash(
                    listing['title'],
                    listing['price'],
                    listing['location']
                )

                from datetime import datetime
                from src.models.schemas import Listing

                listing_obj = Listing(
                    listing_id=listing['listing_id'],
                    title=listing['title'],
                    description=listing['description'],
                    price_eur=listing['price'],
                    seller_location=listing['location'],
                    listing_url=listing['url'],
                    category=listing['category'],
                    content_hash=content_hash,
                    date_posted=datetime.now()
                )

                # Set matched IDs
                if listing.get('matched_case_id'):
                    listing_obj.matched_case_id = listing['matched_case_id']
                    listing_obj.case_confidence_score = listing.get('confidence_score')
                    listing_obj.case_match_method = listing.get('match_method')
                elif listing.get('matched_psu_id'):
                    listing_obj.matched_psu_id = listing['matched_psu_id']
                    listing_obj.psu_confidence_score = listing.get('confidence_score')
                    listing_obj.psu_match_method = listing.get('match_method')

                # Save
                with get_session() as session:
                    existing = ListingRepository.get_by_id(session, listing_obj.listing_id)
                    if existing:
                        print("Updating existing listing...")
                        # Save version
                        ListingRepository.save_version(session, listing_obj.listing_id)
                        # Update
                        from sqlalchemy import text
                        session.execute(text("""
                            UPDATE listings
                            SET title = :title, description = :desc, price_eur = :price,
                                seller_location = :loc, matched_case_id = :case_id,
                                matched_psu_id = :psu_id, case_confidence_score = :case_conf,
                                case_match_method = :case_method, psu_confidence_score = :psu_conf,
                                psu_match_method = :psu_method, updated_at = NOW()
                            WHERE listing_id = :id
                        """), {
                            "id": listing_obj.listing_id,
                            "title": listing_obj.title,
                            "desc": listing_obj.description,
                            "price": listing_obj.price_eur,
                            "loc": listing_obj.seller_location,
                            "case_id": getattr(listing_obj, 'matched_case_id', None),
                            "psu_id": getattr(listing_obj, 'matched_psu_id', None),
                            "case_conf": getattr(listing_obj, 'case_confidence_score', None),
                            "case_method": getattr(listing_obj, 'case_match_method', None),
                            "psu_conf": getattr(listing_obj, 'psu_confidence_score', None),
                            "psu_method": getattr(listing_obj, 'psu_match_method', None)
                        })
                    else:
                        print("Creating new listing...")
                        session.execute(text("""
                            INSERT INTO listings (listing_id, title, description, price_eur,
                                seller_location, listing_url, category, matched_case_id,
                                matched_psu_id, case_confidence_score, case_match_method,
                                psu_confidence_score, psu_match_method, content_hash, is_active)
                            VALUES (:id, :title, :desc, :price, :loc, :url, :cat,
                                :case_id, :psu_id, :case_conf, :case_method, :psu_conf,
                                :psu_method, :hash, true)
                        """), {
                            "id": listing_obj.listing_id,
                            "title": listing_obj.title,
                            "desc": listing_obj.description,
                            "price": listing_obj.price_eur,
                            "loc": listing_obj.seller_location,
                            "url": listing_obj.listing_url,
                            "cat": listing_obj.category,
                            "case_id": getattr(listing_obj, 'matched_case_id', None),
                            "psu_id": getattr(listing_obj, 'matched_psu_id', None),
                            "case_conf": getattr(listing_obj, 'case_confidence_score', None),
                            "case_method": getattr(listing_obj, 'case_match_method', None),
                            "psu_conf": getattr(listing_obj, 'psu_confidence_score', None),
                            "psu_method": getattr(listing_obj, 'psu_match_method', None),
                            "hash": listing_obj.content_hash
                        })
                    session.commit()
                print("✅ Saved to database!")
            except Exception as e:
                print(f"❌ Failed to save: {e}")
                import traceback
                traceback.print_exc()

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_andele(args: argparse.Namespace) -> int:
    """Test single Andele URL."""
    from src.scraper.andele_scraper import AndeleScraper

    print(f"Testing Andele URL: {args.url}")
    print("=" * 50)

    # Determine category
    category = 'general'
    if args.gpu:
        category = 'gpu'
    elif args.cpu:
        category = 'cpu'
    elif args.ssd:
        category = 'ssd'
    elif args.ram:
        category = 'ram'
    elif args.psu:
        category = 'psu'
    elif args.monitors:
        category = 'monitor'
    elif args.motherboards:
        category = 'motherboard'

    try:
        scraper = AndeleScraper(dry_run=not args.save)
        result = scraper.test_url(args.url, category)

        if not result or 'error' in result:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
            return 1

        print("\n✅ Parsed successfully!")
        print("-" * 50)
        print(f"ID:          {result.get('listing_id', 'N/A')}")
        print(f"Title:       {result.get('title', 'N/A')}")
        print(f"Price:       €{result.get('price_eur', 'N/A')}")
        print(f"Location:    {result.get('seller_location', 'N/A')}")
        print(f"Date:        {result.get('date_posted', 'N/A')}")
        print(f"Category:    {result.get('category', category)}")
        print(f"Images:      {result.get('image_count', 0)}")

        if result.get('description_preview'):
            print(f"\nDescription Preview:")
            print(f"  {result['description_preview'][:200]}...")

        if result.get('match'):
            print("\nMATCH RESULTS:")
            print("-" * 50)
            for component_type, match_info in result['match'].items():
                print(f"  {component_type.upper()}:")
                print(f"    ID:         {match_info.get('id')}")
                print(f"    Confidence: {match_info.get('confidence', 0):.0%}")
                print(f"    Method:     {match_info.get('method', 'N/A')}")

        # Save if requested
        if args.save:
            print("\n💾 Saved to database")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _test_url_laptops(args: argparse.Namespace) -> int:
    """Test single Laptop URL."""
    print(f"Testing Laptop URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        from src.scraper.crawler import Crawler, ErrorType
        from src.scraper.laptop_scraper import LaptopScraper, LaptopParser

        # Initialize database
        init_database(config.database)

        crawler = Crawler(config.scraper)
        scraper = LaptopScraper(config, crawler)

        # Extract listing ID from URL
        import re
        match = re.search(r'/([a-z]+)\.html$', args.url)
        if not match:
            print("Could not extract listing ID from URL")
            return 1
        listing_id = match.group(1)

        result = crawler.fetch(args.url)
        if result.error_type != ErrorType.SUCCESS:
            print(f"Failed to fetch: {result.error_msg}")
            return 1

        parser = LaptopParser()
        listing = parser.parse_listing_page(result.html, listing_id, args.url)
        if not listing:
            print("Failed to parse laptop listing")
            return 1

        listing['content_hash'] = "test"

        print("\nLISTING DATA:")
        print("-" * 50)
        print(f"ID:          {listing['listing_id']}")
        print(f"Title:       {listing['title']}")
        print(f"Price:       EUR {listing['price']:.2f}")
        print(f"Location:    {listing.get('location') or 'N/A'}")
        print(f"Brand:       {listing.get('brand') or 'N/A'}")
        print(f"Model:       {listing.get('model') or 'N/A'}")
        print(f"Display:     {listing.get('display_size') or 'N/A'}")
        print(f"CPU:         {listing.get('cpu_raw') or 'N/A'}")
        print(f"CPU Freq:    {listing.get('cpu_freq_ghz') or 'N/A'}")
        print(f"RAM:         {listing.get('ram_gb') or 'N/A'} GB")
        print(f"Storage:     {listing.get('storage_gb') or 'N/A'} GB {listing.get('storage_type') or ''}".strip())
        print(f"GPU:         {listing.get('gpu_raw') or 'N/A'}")
        print(f"Condition:   {listing.get('condition_state') or 'N/A'}")
        print(f"Image:       {listing.get('image_url') or 'N/A'}")

        if args.save:
            saved = scraper._save_listing(listing)
            if saved:
                print("\n✅ Listing saved to database")
            else:
                print("\n❌ Failed to save listing")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


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


def _test_url_ram(args: argparse.Namespace) -> int:
    """Test single RAM URL."""
    from src.models.schemas import RAMMatchResult

    print(f"Testing RAM URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        scraper = RAMScraper(config)
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

            if listing.matched_ram_id:
                print("\nRAM MATCH:")
                print("-" * 50)
                ram = scraper.matcher.get_ram_by_id(listing.matched_ram_id)
                if ram:
                    print(f"Name:        {ram.name}")
                    print(f"Speed:       {ram.speed}")
                    print(f"Modules:     {ram.modules}")
                    if ram.capacity_gb:
                        print(f"Capacity:    {ram.capacity_gb} GB")
                    if ram.cas_latency:
                        print(f"CAS Latency: {ram.cas_latency}")
                    print(f"Confidence:  {listing.ram_confidence_score:.1%}")
                    print(f"Method:      {listing.ram_match_method}")
            else:
                print("\nNo RAM match found")

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
        listings_unmatched = session.execute(text("SELECT COUNT(*) FROM listings WHERE matched_gpu_id IS NULL AND matched_cpu_id IS NULL AND matched_ssd_id IS NULL AND matched_ram_id IS NULL")).scalar()

        gpu_count = session.execute(text("SELECT COUNT(*) FROM gpu_reference")).scalar()
        cpu_count = session.execute(text("SELECT COUNT(*) FROM cpu_reference")).scalar()
        ssd_count = session.execute(text("SELECT COUNT(*) FROM ssd_reference")).scalar()
        ram_count = session.execute(text("SELECT COUNT(*) FROM ram_reference")).scalar()

        gpu_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'gpu'")).scalar()
        cpu_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'cpu'")).scalar()
        ssd_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'ssd'")).scalar()
        ram_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'ram'")).scalar()

        price_entries = session.execute(text("SELECT COUNT(*) FROM price_history")).scalar()

        print("DATABASE STATISTICS")
        print("=" * 50)
        print(f"GPU References:        {gpu_count}")
        print(f"CPU References:        {cpu_count}")
        print(f"SSD References:        {ssd_count}")
        print(f"RAM References:        {ram_count}")
        print(f"Total Listings:        {listings_total}")
        print(f"  - GPU Listings:      {gpu_listings}")
        print(f"  - CPU Listings:      {cpu_listings}")
        print(f"  - SSD Listings:      {ssd_listings}")
        print(f"  - RAM Listings:      {ram_listings}")
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

        # Top RAM by listing count
        print("\nTOP RAM BY LISTINGS:")
        print("-" * 50)
        top_rams = session.execute(text("""
            SELECT r.name, r.speed, COUNT(*) as cnt
            FROM listings l
            JOIN ram_reference r ON l.matched_ram_id = r.id
            WHERE l.is_active = true AND l.category = 'ram'
            GROUP BY r.id, r.name, r.speed
            ORDER BY cnt DESC
            LIMIT 5
        """)).fetchall()

        for ram in top_rams:
            print(f"  {ram['name']} ({ram['speed']}): {ram['cnt']} listings")

        # Motherboard stats
        print("\nMOTHERBOARD STATS:")
        print("-" * 50)
        mb_count = session.execute(text("SELECT COUNT(*) FROM motherboard_models")).scalar()
        mb_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'motherboard'")).scalar()
        print(f"  Models in DB: {mb_count}")
        print(f"  Listings:     {mb_listings}")

        # Monitor stats
        print("\nMONITOR STATS:")
        print("-" * 50)
        mon_count = session.execute(text("SELECT COUNT(*) FROM monitor_models")).scalar()
        mon_listings = session.execute(text("SELECT COUNT(*) FROM listings WHERE category = 'monitor'")).scalar()
        print(f"  Models in DB: {mon_count}")
        print(f"  Listings:     {mon_listings}")

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
        print(f"  SSD Path:    /lv/electronics/computers/completing-pc/ssd/")
        print(f"  RAM Path:    /lv/electronics/computers/completing-pc/ram/")
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


def _test_url_motherboard(args: argparse.Namespace) -> int:
    """Test single Motherboard URL."""
    print(f"Testing Motherboard URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        scraper = MotherboardScraper(config)
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
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Category:    {listing.category}")

            if listing.motherboard_model_id:
                print("\nMOTHERBOARD MATCH:")
                print("-" * 50)
                mb = scraper.matcher.get_mb_by_id(listing.motherboard_model_id)
                if mb:
                    print(f"Brand:       {mb.brand}")
                    print(f"Model:       {mb.model}")
                    print(f"Socket:      {mb.socket or 'N/A'}")
                    print(f"Chipset:     {mb.chipset or 'N/A'}")
                    print(f"Confidence:  {listing.motherboard_confidence_score:.1%}")
                    print(f"Method:      {listing.motherboard_match_method}")
            else:
                print("\nNo Motherboard match found")

            if args.save_html:
                print(f"\nHTML saved to logs/html_samples/")

            return 0
        else:
            print("Failed to parse listing")
            return 1

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_monitor(args: argparse.Namespace) -> int:
    """Test single Monitor URL."""
    print(f"Testing Monitor URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        scraper = MonitorScraper(config)
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
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Category:    {listing.category}")

            if listing.monitor_model_id:
                print("\nMONITOR MATCH:")
                print("-" * 50)
                mon = scraper.matcher.get_monitor_by_id(listing.monitor_model_id)
                if mon:
                    print(f"Brand:       {mon.brand}")
                    print(f"Model:       {mon.model}")
                    print(f"Size:        {mon.size or 'N/A'}")
                    print(f"Resolution:  {mon.resolution or 'N/A'}")
                    print(f"Refresh:     {mon.refresh_rate or 'N/A'}")
                    print(f"Panel:       {mon.panel_type or 'N/A'}")
                    print(f"Confidence:  {listing.monitor_confidence_score:.1%}")
                    print(f"Method:      {listing.monitor_match_method}")
            else:
                print("\nNo Monitor match found")

            if args.save_html:
                print(f"\nHTML saved to logs/html_samples/")

            return 0
        else:
            print("Failed to parse listing")
            return 1

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_console(args: argparse.Namespace) -> int:
    """Test single Console URL."""
    print(f"Testing Console URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        from src.database.connection import init_database, get_session
        from src.scraper.crawler import Crawler, ErrorType
        from src.database.repository import ConsoleRepository, ConsoleVariantRepository, ConsoleEditionRepository
        from src.scraper.console_matcher import ConsoleMatcher
        from bs4 import BeautifulSoup
        import re

        # Initialize database
        init_database(config.database)

        crawler = Crawler(config.scraper)

        # Load matchers
        with get_session() as session:
            consoles = ConsoleRepository.get_all(session) if hasattr(ConsoleRepository, 'get_all') else []
            variants = ConsoleVariantRepository.get_all(session) if hasattr(ConsoleVariantRepository, 'get_all') else []
            editions = ConsoleEditionRepository.get_all(session) if hasattr(ConsoleEditionRepository, 'get_all') else []

        # Fetch and parse
        result = crawler.fetch(args.url)

        if result.error_type != ErrorType.SUCCESS:
            print(f"Failed to fetch: {result.error_msg}")
            return 1

        # Extract listing ID from URL
        match = re.search(r'/([a-z]+)\.html$', args.url)
        if not match:
            print("Could not extract listing ID from URL")
            return 1

        listing_id = match.group(1)

        # Parse with BeautifulSoup
        soup = BeautifulSoup(result.html, 'html.parser')

        # Extract title
        title_elem = soup.find('title')
        title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""

        # Extract description
        msg_div = soup.find('div', {'id': 'msg_div_msg'})
        description = ""
        if msg_div:
            description = msg_div.get_text(separator=' ', strip=True)

        # Extract price
        price = 0.0
        price_cell = soup.find('td', {'class': 'ads_price'})
        if price_cell:
            price_text = price_cell.get_text(strip=True)
            price_match = re.search(r'([\d,]+)', price_text.replace(' ', ''))
            if price_match:
                price_str = price_match.group(1).replace(',', '.')
                try:
                    price = float(price_str)
                except ValueError:
                    pass

        # Extract location
        location = ""
        for row in soup.find_all('tr'):
            label = row.find('td', {'class': 'ads_contacts_name'})
            if label and 'vieta' in label.get_text(strip=True).lower():
                value_cell = row.find('td', {'class': 'ads_contacts'})
                if value_cell:
                    location = value_cell.get_text(strip=True)
                    break

        if not location:
            address = soup.find('td', {'class': 'td_address'})
            if address:
                location = address.get_text(strip=True)

        # Check skip patterns (stores, rentals, emulators)
        skip_patterns = [
            'nopirkšu', 'pērku', 'remonts', 'internetveikals',
            'nopirksu', 'perku', 'remont', 'internet veikals',
            'veikals', 'īre', 'īres', 'iznomāt', 'emulators', 'emulatorus'
        ]
        full_text_lower = (title + ' ' + description).lower()
        for pattern in skip_patterns:
            if pattern in full_text_lower:
                print(f"\nSKIPPED: Listing contains skip pattern '{pattern}'")
                print(f"Title: {title}")
                return 0

        listing = {
            'listing_id': listing_id,
            'title': title,
            'description': description,
            'price_eur': price,
            'seller_location': location,
            'listing_url': args.url,
            'category': 'console'
        }

        # Match using ConsoleMatcher - pass title and description separately
        matcher = ConsoleMatcher(consoles, variants, editions)
        match_result = matcher.match(title, description, price=price)

        # Output
        print("\nLISTING DATA:")
        print("-" * 50)
        print(f"ID:          {listing['listing_id']}")
        print(f"Title:       {listing['title']}")
        print(f"Price:       EUR {listing['price_eur']:.2f}" if listing['price_eur'] > 0 else "Price:       N/A")
        print(f"Location:    {listing.get('seller_location', 'N/A')}")
        print(f"Category:    {listing['category'].upper()}")

        if match_result.console:
            print("\nCONSOLE MATCH:")
            print("-" * 50)
            print(f"Console:     {match_result.console.name}")
            print(f"Company:     {match_result.console.company or 'N/A'}")
            print(f"Generation:  {match_result.console.generation or 'N/A'}")
            print(f"Confidence:  {match_result.console_confidence:.1%}")
            print(f"Method:      {match_result.method}")

            if match_result.variant:
                print("\nVARIANT MATCH:")
                print("-" * 50)
                print(f"Model:       {match_result.variant.model_name}")
                print(f"SKU:         {match_result.variant.sku or 'N/A'}")
                print(f"Storage:     {match_result.variant.storage_gb or 'N/A'} GB")
                print(f"Confidence:  {match_result.variant_confidence:.1%}")

            if match_result.edition:
                print("\nEDITION MATCH:")
                print("-" * 50)
                print(f"Edition:     {match_result.edition.edition_name}")
                print(f"Color:       {match_result.edition.color or 'N/A'}")
                print(f"Features:    {match_result.edition.special_features or 'N/A'}")
                print(f"Confidence:  {match_result.edition_confidence:.1%}")

            if match_result.is_special:
                print("\nSPECIAL EDITION:")
                print("-" * 50)
                print(f"Note:        {match_result.special_note or 'N/A'}")
        else:
            print("\nNo console match found")
            print("\nTop candidates:")
            candidates = matcher.get_candidates(title + ' ' + description, limit=5)
            for console, score in candidates:
                print(f"  - {console.name} - score: {score:.1%}")

        # Save to database if --save flag
        if getattr(args, 'save', False):
            print("\n" + "-" * 50)
            print("Save functionality not implemented yet")

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_lens(args: argparse.Namespace) -> int:
    """Test single Lens URL."""
    print(f"Testing Lens URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        from src.scraper.crawler import Crawler, ErrorType
        from src.scraper.lens_scraper import LensScraper

        crawler = Crawler(config.scraper)

        # Fetch the page
        result = crawler.fetch(args.url)

        if result.error_type != ErrorType.SUCCESS:
            print(f"Failed to fetch: {result.error_msg}")
            return 1

        # Extract listing ID from URL
        import re
        match = re.search(r'/([a-z0-9]+)\.html$', args.url)
        if not match:
            print("Could not extract listing ID from URL")
            return 1

        listing_id = match.group(1)

        # Create scraper instance
        scraper = LensScraper(config)
        scraper.initialize()

        # Scrape the listing
        listing = scraper.scrape_listing(listing_id, args.url)

        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            print(f"Title:       {listing.title}")
            print(f"Price (EUR): {listing.price_eur}")
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Category:    {listing.category}")

            if hasattr(listing, 'matched_lens_id') and listing.matched_lens_id:
                print(f"\nLENS MATCH:")
                print("-" * 50)
                print(f"Matched ID:  {listing.matched_lens_id}")
                print(f"Confidence:  {listing.lens_confidence_score:.0%}")
                print(f"Method:      {listing.lens_match_method}")
            else:
                print("\nNo lens match found")
        else:
            print("\nListing was filtered or could not be parsed")

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_camera(args: argparse.Namespace) -> int:
    """Test single Camera URL."""
    print(f"Testing Camera URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        scraper = CameraScraper(config)
        scraper.initialize()

        listing = scraper.test_url(args.url)

        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            print(f"Title:       {listing.title}")
            print(f"Price (EUR): {listing.price_eur}")
            print(f"Location:    {listing.seller_location or 'N/A'}")
            print(f"Category:    {listing.category}")

            if listing.matched_camera_id:
                print(f"\nCAMERA MATCH:")
                print("-" * 50)
                camera = scraper.matcher.get_camera_by_id(listing.matched_camera_id)
                if camera:
                    print(f"Brand:       {camera.get('brand')}")
                    print(f"Model:       {camera.get('model')}")
                    print(f"Mount:       {camera.get('mount') or 'N/A'}")
                    print(f"Sensor:      {camera.get('sensor') or 'N/A'}")
                    print(f"Confidence:  {listing.camera_confidence_score:.0%}")
                    print(f"Method:      {listing.camera_match_method}")

                # Show matched lenses
                if listing.description and "Lenses detected:" in listing.description:
                    print(f"\nLENSES DETECTED:")
                    print("-" * 50)
                    lens_info = listing.description.split("Lenses detected:")[-1].strip()
                    print(lens_info)
            else:
                print("\nNo camera match found")
                print("\nTop candidates:")
                candidates = scraper.matcher.get_candidates(listing.title, limit=5)
                for camera, score in candidates:
                    print(f"  - {camera.get('brand')} {camera.get('model')} - score: {score:.1%}")
        else:
            print("\nListing was filtered or could not be parsed")

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _scrape_computers(args: argparse.Namespace) -> int:
    """Execute Computer scrape."""
    print("\n" + "=" * 50)
    print("Starting Computer Scraper...")
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

    print("-" * 50)

    try:
        scraper = ComputerScraper(config)
        stats = scraper.run()

        print("\n" + "=" * 50)
        print("COMPUTER SCRAPE SUMMARY")
        print("=" * 50)
        print(f"Total processed:     {stats['total']}")
        print(f"New listings:        {stats['new']}")
        print(f"Price updates:       {stats['updated']}")
        print(f"Unchanged:           {stats['unchanged']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Skipped:             {stats['skipped']}")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\nComputer Scrape Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def _test_url_computers(args: argparse.Namespace) -> int:
    """Test single Computer URL."""
    print(f"Testing Computer URL: {args.url}")
    print("=" * 50)

    config = AppConfig.from_yaml()
    config.scraper.test_mode = True
    config.scraper.save_html_samples = args.save_html

    try:
        scraper = ComputerScraper(config)
        scraper.initialize()

        listing, match_result = scraper.scrape_single(args.url)

        if listing:
            print("\nLISTING DATA:")
            print("-" * 50)
            print(f"ID:          {listing.listing_id}")
            print(f"Title:       {listing.title}")
            print(f"Price:       EUR {listing.price_eur:.2f}")
            print(f"Location:    {listing.seller_location or 'N/A'}")

            print(f"\n{'='*50}")
            print("MATCHED COMPONENTS:")
            print("="*50)

            if listing.matched_cpu_id:
                cpu_data = scraper.matcher.get_component_by_id('cpu', listing.matched_cpu_id)
                cpu_name = cpu_data.get('processor_number') or cpu_data.get('model', 'Unknown')
                print(f"\n🖥️  CPU: {cpu_name} ({listing.cpu_confidence:.1%} confidence)")
                print(f"    ID: {listing.matched_cpu_id}")
                print(f"    Match Method: {listing.cpu_match_method}")
                print(f"    Brand: {cpu_data.get('brand', 'N/A')}")
                print(f"    Socket: {cpu_data.get('socket') or 'N/A'}")
                cores = cpu_data.get('cores') or 'N/A'
                threads = cpu_data.get('threads') or 'N/A'
                print(f"    Cores/Threads: {cores}/{threads}")
                cpu_price = cpu_data.get('price') or 150
                print(f"    Avg Price: EUR {cpu_price:.2f}")
            else:
                print("\n🖥️  CPU: Not detected")

            if listing.matched_gpu_id:
                gpu_data = scraper.matcher.get_component_by_id('gpu', listing.matched_gpu_id)
                gpu_name = gpu_data.get('name') or gpu_data.get('model', 'Unknown')
                print(f"\n🎮 GPU: {gpu_name} ({listing.gpu_confidence:.1%} confidence)")
                print(f"    ID: {listing.matched_gpu_id}")
                print(f"    Match Method: {listing.gpu_match_method}")
                print(f"    Brand: {gpu_data.get('brand', 'N/A')}")
                vram = gpu_data.get('vram_gb')
                vram_display = f"{vram} GB" if vram else 'N/A'
                print(f"    VRAM: {vram_display}")
                msrp = gpu_data.get('msrp_usd')
                gpu_price = (msrp * 0.85) if msrp else 200.0
                print(f"    Est. Price: EUR {gpu_price:.2f}")
            else:
                print("\n🎮 GPU: Not detected")

            if listing.matched_ram_id:
                # Handle synthetic RAM (negative ID) differently
                if listing.matched_ram_id < 0 and match_result and match_result.ram:
                    ram = match_result.ram
                    if isinstance(ram, dict):
                        ram_name = ram.get('name') or ram.get('brand', '') + ' ' + ram.get('model', '')
                        ram_name = ram_name.strip() or 'Generic RAM'
                        capacity = ram.get('capacity_gb')
                        speed = ram.get('speed_mhz')
                        ram_price = ram.get('price') or 50
                    else:
                        ram_name = ram.name if hasattr(ram, 'name') else str(ram)
                        capacity = ram.capacity_gb if hasattr(ram, 'capacity_gb') else None
                        speed = ram.speed_mhz if hasattr(ram, 'speed_mhz') else None
                        ram_price = 50
                    print(f"\n💾 RAM: {ram_name} ({listing.ram_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_ram_id} (synthetic)")
                    print(f"    Match Method: {listing.ram_match_method}")
                    print(f"    Capacity: {capacity} GB" if capacity else "    Capacity: N/A")
                    print(f"    Speed: {speed} MHz" if speed else "    Speed: N/A")
                    print(f"    Price: EUR {ram_price:.2f}")
                elif listing.matched_ram_id > 0:
                    ram_data = scraper.matcher.get_component_by_id('ram', listing.matched_ram_id)
                    ram_name = ram_data.get('name') or 'Unknown'
                    print(f"\n💾 RAM: {ram_name} ({listing.ram_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_ram_id}")
                    print(f"    Match Method: {listing.ram_match_method}")
                    capacity = ram_data.get('capacity_gb')
                    print(f"    Capacity: {capacity} GB" if capacity else "    Capacity: N/A")
                    speed = ram_data.get('speed_mhz')
                    print(f"    Speed: {speed} MHz" if speed else "    Speed: N/A")
                    ram_price = ram_data.get('price') or 50
                    print(f"    Price: EUR {ram_price:.2f}")
            elif listing.ram_match_method and 'fallback' in listing.ram_match_method:
                # Display fallback RAM - extract from method name
                # e.g., "fallback_ddr4_16gb" -> "16GB DDR4"
                method_parts = listing.ram_match_method.replace('fallback_', '').split('_')
                if len(method_parts) >= 2:
                    ddr_type = method_parts[0].upper()
                    capacity = method_parts[1].replace('gb', '')
                    print(f"\n💾 RAM: Generic {capacity}GB {ddr_type} ({listing.ram_confidence:.1%} confidence)")
                    print(f"    Match Method: {listing.ram_match_method}")
                    # Estimate price based on capacity
                    cap_int = int(capacity) if capacity.isdigit() else 16
                    price = 25 if cap_int <= 16 else 50
                    print(f"    Price: EUR {price:.2f}")
                else:
                    print(f"\n💾 RAM: Generic RAM ({listing.ram_confidence:.1%} confidence)")
                    print(f"    Match Method: {listing.ram_match_method}")
            else:
                print("\n💾 RAM: Not detected")

            if listing.matched_ssd_id:
                # Handle synthetic SSDs (negative ID) differently
                if listing.matched_ssd_id < 0 and match_result and match_result.ssd:
                    # Display synthetic SSD directly from match_result
                    ssd = match_result.ssd
                    if isinstance(ssd, dict):
                        ssd_name = ssd.get('brand', '') + ' ' + ssd.get('model', '')
                        ssd_name = ssd_name.strip() or 'Generic SSD'
                        capacity = ssd.get('capacity_gb')
                        ssd_price = ssd.get('price') or 50
                    else:
                        ssd_name = f"{ssd.brand} {ssd.model}"
                        capacity = ssd.capacity_gb
                        ssd_price = 50
                    print(f"\n💿 SSD: {ssd_name} ({listing.ssd_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_ssd_id} (synthetic)")
                    print(f"    Match Method: {listing.ssd_match_method}")
                    print(f"    Capacity: {capacity} GB" if capacity else "    Capacity: N/A")
                    print(f"    Price: EUR {ssd_price:.2f}")
                else:
                    ssd_data = scraper.matcher.get_component_by_id('ssd', listing.matched_ssd_id)
                    ssd_name = ssd_data.get('model') or ssd_data.get('name', 'Unknown')
                    print(f"\n💿 SSD: {ssd_name} ({listing.ssd_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_ssd_id}")
                    print(f"    Match Method: {listing.ssd_match_method}")
                    capacity = ssd_data.get('capacity_gb')
                    print(f"    Capacity: {capacity} GB" if capacity else "    Capacity: N/A")
                    print(f"    Type: {ssd_data.get('type', 'N/A')}")
                    ssd_price = ssd_data.get('price') or 50
                    print(f"    Price: EUR {ssd_price:.2f}")
            elif match_result and match_result.ssd:
                # SSD matched but ID not stored - display from match_result
                ssd = match_result.ssd
                if isinstance(ssd, dict):
                    ssd_name = ssd.get('brand', '') + ' ' + ssd.get('model', '')
                    ssd_name = ssd_name.strip() or 'Generic SSD'
                    capacity = ssd.get('capacity_gb')
                    ssd_id = ssd.get('id', 'N/A')
                else:
                    ssd_name = f"{ssd.brand} {ssd.model}"
                    capacity = ssd.capacity_gb
                    ssd_id = getattr(ssd, 'id', 'N/A')
                print(f"\n💿 SSD: {ssd_name} ({listing.ssd_confidence:.1%} confidence)")
                print(f"    ID: {ssd_id}")
                print(f"    Match Method: {listing.ssd_match_method}")
                print(f"    Capacity: {capacity} GB" if capacity else "    Capacity: N/A")
                print(f"    Price: EUR 50.00")
            elif listing.ssd_match_method and listing.ssd_match_method.startswith('fallback'):
                # Display fallback SSD
                ssd_capacity = listing.ssd_match_method.replace('fallback_', '').replace('gb_ssd', '')
                print(f"\n💿 SSD: Generic {ssd_capacity}GB SSD (50.0% confidence)")
                print(f"    Match Method: {listing.ssd_match_method}")
                print(f"    Capacity: {ssd_capacity} GB")
                print(f"    Type: SATA")
            else:
                print("\n💿 SSD: Not detected")

            # Display additional SSDs (SSD2, SSD3)
            if match_result and match_result.additional_ssds:
                for i, ssd in enumerate(match_result.additional_ssds, 2):
                    print(f"\n💿 SSD {i}: {ssd.get('brand', 'Generic')} {ssd.get('capacity_gb')}GB")
                    print(f"    Match Method: additional_ssd")
                    print(f"    Capacity: {ssd.get('capacity_gb')} GB")
                    print(f"    Type: {ssd.get('type', 'SATA')}")
                    print(f"    Price: EUR {ssd.get('price', 50):.2f}")
            elif listing.matched_ssd2_id:
                # SSD2 in database but not in match_result - show from DB
                print(f"\n💿 SSD 2: Generic (ID: {listing.matched_ssd2_id})")
                if listing.ssd2_match_method:
                    import re
                    cap_match = re.search(r'(\d+)', listing.ssd2_match_method)
                    if cap_match:
                        print(f"    Capacity: {cap_match.group(1)} GB")

            if listing.matched_psu_id:
                # Handle synthetic PSUs (negative ID) differently
                if listing.matched_psu_id < 0 and match_result and match_result.psu:
                    psu = match_result.psu
                    if isinstance(psu, dict):
                        psu_name = psu.get('brand', '') + ' ' + psu.get('model', '')
                        psu_name = psu_name.strip() or 'Generic PSU'
                        wattage = psu.get('wattage')
                        psu_price = psu.get('price') or 55
                    else:
                        psu_name = f"{psu.brand} {psu.model}"
                        wattage = psu.wattage
                        psu_price = 55
                    print(f"\n⚡ PSU: {psu_name} ({listing.psu_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_psu_id} (synthetic)")
                    print(f"    Match Method: {listing.psu_match_method}")
                    print(f"    Wattage: {wattage}W" if wattage else "    Wattage: N/A")
                    print(f"    Price: EUR {psu_price:.2f}")
                else:
                    psu_data = scraper.matcher.get_component_by_id('psu', listing.matched_psu_id)
                    psu_name = psu_data.get('model') or psu_data.get('name', 'Unknown')
                    print(f"\n⚡ PSU: {psu_name} ({listing.psu_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_psu_id}")
                    print(f"    Match Method: {listing.psu_match_method}")
                    wattage = psu_data.get('wattage')
                    print(f"    Wattage: {wattage}W" if wattage else "    Wattage: N/A")
                    psu_price = psu_data.get('price') or 55
                    print(f"    Price: EUR {psu_price:.2f}")
            else:
                print(f"\n⚡ PSU: Not detected (Fallback: {listing.fallback_psu_wattage}W)")

            if listing.matched_case_id:
                # Handle synthetic Cases (negative ID) differently
                if listing.matched_case_id < 0 and match_result and match_result.case:
                    case = match_result.case
                    if isinstance(case, dict):
                        case_name = case.get('brand', '') + ' ' + case.get('model', '')
                        case_name = case_name.strip() or 'Generic Case'
                        case_price = case.get('price') or 15
                    else:
                        case_name = f"{case.brand} {case.model}"
                        case_price = 15
                    print(f"\n📦 Case: {case_name} ({listing.case_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_case_id} (synthetic)")
                    print(f"    Match Method: {listing.case_match_method}")
                    print(f"    Price: EUR {case_price:.2f}")
                else:
                    case_data = scraper.matcher.get_component_by_id('case', listing.matched_case_id)
                    case_name = case_data.get('model') or case_data.get('name', 'Unknown')
                    print(f"\n📦 Case: {case_name} ({listing.case_confidence:.1%} confidence)")
                    print(f"    ID: {listing.matched_case_id}")
                    print(f"    Match Method: {listing.case_match_method}")
                    case_price = case_data.get('price') or 15
                    print(f"    Price: EUR {case_price:.2f}")
            else:
                print(f"\n📦 Case: Not detected (Fallback: EUR {listing.fallback_case_price:.2f})")

            # Show motherboard match if available
            if match_result and match_result.motherboard:
                mb = match_result.motherboard
                print(f"\n🔌 Motherboard: {mb.get('brand', '')} {mb.get('model', '')} ({match_result.motherboard_confidence:.1%} confidence)")
                print(f"    ID: {mb.get('id')}")
                print(f"    Match Method: {match_result.motherboard_method}")
                print(f"    Socket: {mb.get('socket', 'N/A')}")
                print(f"    Chipset: {mb.get('chipset', 'N/A')}")
            elif listing.fallback_motherboard_price:
                print(f"\n🔌 Motherboard: Not detected (Fallback: EUR {listing.fallback_motherboard_price:.2f})")

            # Show monitor match if available
            if match_result and match_result.monitor:
                mon = match_result.monitor
                print(f"\n🖥️  Monitor: {mon.get('brand', '')} {mon.get('model', '')} ({match_result.monitor_confidence:.1%} confidence)")
                print(f"    Size: {mon.get('size', 'N/A')}\"")
                print(f"    Resolution: {mon.get('resolution', 'N/A')}")
                if mon.get('refresh_rate'):
                    print(f"    Refresh Rate: {mon.get('refresh_rate')}Hz")
                print(f"    Match Method: {match_result.monitor_method}")
            else:
                print(f"\n🖥️  Monitor: Not detected")

            print(f"\n{'='*50}")
            print("PRICE BREAKDOWN:")
            print("="*50)
            print(f"Component Total:    EUR {listing.components_total_eur:.2f}")
            print(f"Listing Price:      EUR {listing.price_eur:.2f}")
            diff_color = "🟢" if listing.price_difference_eur >= 0 else "🔴"
            print(f"Price Difference:   {diff_color} EUR {listing.price_difference_eur:+.2f}")

            if listing.fallback_motherboard_price and not (match_result and match_result.motherboard):
                print(f"Motherboard:        EUR {listing.fallback_motherboard_price:.2f} (estimated)")
        else:
            print("\nListing was filtered or could not be parsed")

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


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
