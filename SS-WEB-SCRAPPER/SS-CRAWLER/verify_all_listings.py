import sys
sys.path.insert(0, 'src')
import psycopg2
from src.scraper.computer_scraper import ComputerScraper

# URLs to test
urls = [
    ("https://www.ss.com/msg/lv/electronics/computers/pc/fgjlo.html", "fgjlo"),
    ("https://www.ss.com/msg/lv/electronics/computers/pc/aecib.html", "aecib"),
    ("https://www.ss.com/msg/lv/electronics/computers/pc/fbfbc.html", "fbfbc"),
]

# Connect to database
conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)

print("Initializing scraper...")
scraper = ComputerScraper(conn)

# Test each URL
for url, listing_id in urls:
    print(f"\n{'='*60}")
    print(f"Testing: {listing_id}")
    print(f"{'='*60}")
    
    # Scrape the listing
    listing = scraper.scrape_listing(url, listing_id)
    
    if not listing:
        print(f"Failed to scrape {listing_id}")
        continue
    
    print(f"Title: {listing.title}")
    print(f"Price: {listing.price}")
    
    # Get full text
    full_text = f"{listing.title}\n{listing.description}"
    
    # Match components using the scraper's matcher
    result = scraper.matcher.match_listing(full_text, listing.price, listing.location)
    
    print(f"\nResults:")
    print(f"  CPU: {result.cpu.get('cpu_name', 'Not detected') if result.cpu else 'Not detected'} (ID: {result.cpu.get('id', 'N/A')})")
    print(f"  GPU: {result.gpu.get('name', 'Not detected') if result.gpu else 'Not detected'}")
    print(f"  RAM: {result.ram.get('name', 'Not detected') if result.ram else 'Not detected'}")
    print(f"  SSD: {result.ssd.get('name', 'Not detected') if result.ssd else 'Not detected'} (method: {result.ssd_method})")
    print(f"  PSU: {result.psu.get('name', 'Not detected') if result.psu else 'Not detected'} (method: {result.psu_method})")
    print(f"  Case: {result.case.get('name', 'Not detected') if result.case else 'Not detected'} (method: {result.case_method})")
    print(f"  MB: {result.motherboard.get('name', 'Not detected') if result.motherboard else 'Not detected'}")
    print(f"  Monitor: {result.monitor.get('model', 'Not detected') if result.monitor else 'Not detected'}")

conn.close()
