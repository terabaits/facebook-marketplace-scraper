#!/usr/bin/env python3
"""Directly run cases scraper with fixed config."""
import sys
sys.path.insert(0, 'src')

from src.utils.config import AppConfig, DatabaseConfig, ScraperConfig
from src.database.connection import init_database
from src.scraper.cases_scraper import CasesScraper
from src.scraper.crawler import Crawler

# Create config with correct port
database_config = DatabaseConfig(
    host="localhost",
    port=5433,
    name="ss_market",
    user="crawler",
    password="crawler_pass"
)

scraper_config = ScraperConfig()
scraper_config.category_path = "/lv/electronics/computers/completing-pc/cases/"
scraper_config.max_pages = 5

config = AppConfig(
    scraper=scraper_config,
    database=database_config
)

print("=" * 50)
print("Starting Cases Scraper")
print("=" * 50)
print(f"Database: {config.database.host}:{config.database.port}/{config.database.name}")
print(f"Category: {config.scraper.category_path}")
print(f"Max pages: {config.scraper.max_pages}")
print("-" * 50)

# Initialize database
init_database(config.database)

# Create crawler and scraper
crawler = Crawler(config.scraper)
scraper = CasesScraper(config, crawler)

# Run scraper
listings = scraper.scrape_category()

# Get stats
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
