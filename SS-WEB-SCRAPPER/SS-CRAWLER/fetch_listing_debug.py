"""Fetch and display raw listing content for debugging."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from ss_crawler.crawler import SSListingCrawler

# Create a simple fetcher
class DebugCrawler(SSListingCrawler):
    def __init__(self):
        # Skip __init__ that requires config
        self.session = None
        self._init_session()
    
    def _init_session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

crawler = DebugCrawler()

url = "https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html"
try:
    response = crawler.session.get(url, timeout=30)
    response.raise_for_status()
    
    # Save raw HTML
    with open('listing_pbdhn_raw.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"Status: {response.status_code}")
    print(f"Content saved to listing_pbdhn_raw.html")
    
    # Parse and extract text
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get title
    title = soup.find('h2', class_='msg_title')
    if title:
        print(f"\nTitle: {title.get_text(strip=True)}")
    
    # Get body
    body = soup.find('div', id='msg_div_msg')
    if body:
        text = body.get_text(separator=' ', strip=True)
        print(f"\nBody text (first 2000 chars):\n{text[:2000]}")
        
        # Save full text
        with open('listing_pbdhn_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\nFull text saved to listing_pbdhn_text.txt")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
