# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.scraper.computer_scraper import ComputerScraper
from src.utils.config import AppConfig

config = AppConfig()
scraper = ComputerScraper(config)

# Test the full computer scraper
url = "https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html"
print("Testing computer scraper...")
result = scraper.scrape_single_listing(url)
print("Result:", result)
