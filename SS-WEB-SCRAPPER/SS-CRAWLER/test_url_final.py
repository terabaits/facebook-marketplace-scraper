import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.scraper.engine import Scraper
from src.utils.config import AppConfig

config = AppConfig.from_yaml()
scraper = Scraper(config)

url = "https://www.ss.com/msg/lv/electronics/computers/completing-pc/video/nhdnf.html"

print(f"Testing: {url}")
print("=" * 60)

scraper.initialize()
listing, match = scraper.run_single(url)

if listing:
    print(f"\nLISTING DATA:")
    print("-" * 50)
    print(f"ID:       {listing.listing_id}")
    print(f"Title:    {listing.title}")
    print(f"Price:    EUR {listing.price_eur:.2f}")
    if listing.vram_mb:
        print(f"VRAM:     {listing.vram_mb/1024:.1f} GB ({listing.vram_mb} MB)")
    else:
        print("VRAM:     N/A")
    
    if match.gpu:
        print("\nGPU MATCH:")
        print("-" * 50)
        print(f"Model:       {match.gpu.vendor} {match.gpu.model}")
        if match.gpu.vram_gb:
            print(f"VRAM:        {match.gpu.vram_gb/1024:.0f} GB (reference)")
        else:
            print("VRAM:        N/A (reference)")
        print(f"Confidence:  {match.confidence:.1%}")
        print(f"Method:      {match.method}")
    else:
        print("\nNo GPU match found")
else:
    print("Failed to parse listing")

scraper.cleanup()
print("\n" + "=" * 60)
print("Test complete!")
