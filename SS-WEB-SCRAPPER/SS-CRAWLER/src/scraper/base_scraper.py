"""Base scraper class."""
from typing import Optional

from src.scraper.crawler import Crawler
from src.utils.config import AppConfig


class BaseScraper:
    """Base class for scrapers."""
    
    def __init__(self, config: AppConfig, crawler: Optional[Crawler] = None):
        self.config = config
        self.crawler = crawler or Crawler(config.scraper)
