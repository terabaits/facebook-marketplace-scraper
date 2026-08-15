"""
Sony Lens Scraper for lab174.com - API-based approach
Tries to find the underlying data source
"""

import json
import csv
import time
from typing import List, Dict

from playwright.sync_api import sync_playwright


class Lab174APIScraper:
    """Scraper that tries to find and use the internal data API"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.browser = None
        self.page = None
    
    def setup(self):
        """Setup browser"""
        pw = sync_playwright().start()
        self.browser = pw.chromium.launch(headless=True)
        context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = context.new_page()
        print("Browser ready")
    
    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
    
    def get_page_html(self) -> str:
        """Get full HTML of the page"""
        self.page.goto(self.BASE_URL, wait_until='networkidle')
        time.sleep(3)
        return self.page.content()
    
    def is_sony(self, name: str) -> bool:
        """Check if Sony lens"""
        n = name.lower()
        return any(x in n for x in ['sony', 'fe ', 'vario-tessar'])
    
    def scrape(self) -> List[Dict]:
        """Scrape all data"""
        self.setup()
        
        try:
            html = self.get_page_html()
            
            # Parse the table manually
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            table = soup.find('table')
            if not table:
                print("No table found!")
                return []
            
            rows = table.find_all('tr')[1:]  # Skip header
            print(f"Found {len(rows)} rows in table")
            
            all_lenses = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 14:
                    lens = {
                        'lens_name': cells[0].get_text(strip=True),
                        'focal_length_wide': cells[1].get_text(strip=True),
                        'focal_length_tele': cells[2].get_text(strip=True),
                        'f_stop': cells[3].get_text(strip=True),
                        'year': cells[4].get_text(strip=True),
                        'min_focus_distance': cells[5].get_text(strip=True),
                        'max_magnification': cells[6].get_text(strip=True),
                        'weight': cells[7].get_text(strip=True),
                        'weight_class': cells[8].get_text(strip=True),
                        'length': cells[9].get_text(strip=True),
                        'aperture_ring': cells[10].get_text(strip=True),
                        'autofocus': cells[11].get_text(strip=True),
                        'category': cells[12].get_text(strip=True),
                        'macro': cells[13].get_text(strip=True),
                        'price': cells[14].get_text(strip=True) if len(cells) > 14 else '',
                    }
                    all_lenses.append(lens)
            
            # Filter Sony
            sony_lenses = [l for l in all_lenses if self.is_sony(l['lens_name'])]
            
            print(f"Total: {len(all_lenses)} | Sony: {len(sony_lenses)}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close()
    
    def save_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved: {path}")
    
    def save_csv(self, path: str):
        if not self.lenses:
            return
        
        fields = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                 'year', 'min_focus_distance', 'max_magnification', 'weight',
                 'weight_class', 'length', 'aperture_ring', 'autofocus',
                 'category', 'macro', 'price']
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.lenses)
        print(f"Saved: {path}")


def main():
    print("=" * 60)
    print("Lab174 Sony Lens Scraper (API Approach)")
    print("=" * 60)
    
    scraper = Lab174APIScraper()
    
    try:
        lenses = scraper.scrape()
        
        if lenses:
            scraper.save_json('sony_lenses.json')
            scraper.save_csv('sony_lenses.csv')
            
            print("\nSample Sony lenses:")
            for i, l in enumerate(lenses[:5], 1):
                print(f"{i}. {l['lens_name']}")
        else:
            print("No lenses found!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
