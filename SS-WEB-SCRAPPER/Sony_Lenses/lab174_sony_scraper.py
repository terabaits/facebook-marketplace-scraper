"""
Sony Lens Scraper for lab174.com - Complete Working Implementation
Navigates through all pages and extracts Sony lens data
"""

import json
import csv
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright


class Lab174SonyScraper:
    """Complete scraper for Sony lenses from lab174.com"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.browser = None
        self.page = None
    
    def setup(self):
        """Initialize browser"""
        pw = sync_playwright().start()
        self.browser = pw.chromium.launch(headless=True)
        context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = context.new_page()
        print("Browser initialized")
    
    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
    
    def extract_table_data(self) -> List[Dict]:
        """Extract all lens data from current table view"""
        results = []
        
        # Get all rows from table
        rows = self.page.query_selector_all('table tbody tr')
        if not rows:
            rows = self.page.query_selector_all('table tr')[1:]  # Skip header
        
        for row in rows:
            try:
                cells = row.query_selector_all('td')
                if len(cells) >= 14:
                    lens = {
                        'lens_name': cells[0].inner_text().strip(),
                        'focal_length_wide': cells[1].inner_text().strip(),
                        'focal_length_tele': cells[2].inner_text().strip(),
                        'f_stop': cells[3].inner_text().strip(),
                        'year': cells[4].inner_text().strip(),
                        'min_focus_distance': cells[5].inner_text().strip(),
                        'max_magnification': cells[6].inner_text().strip(),
                        'weight': cells[7].inner_text().strip(),
                        'weight_class': cells[8].inner_text().strip(),
                        'length': cells[9].inner_text().strip(),
                        'aperture_ring': cells[10].inner_text().strip(),
                        'autofocus': cells[11].inner_text().strip(),
                        'category': cells[12].inner_text().strip(),
                        'macro': cells[13].inner_text().strip(),
                        'price': cells[14].inner_text().strip() if len(cells) > 14 else '',
                    }
                    results.append(lens)
            except Exception:
                continue
        
        return results
    
    def is_sony_lens(self, name: str) -> bool:
        """Check if a lens is Sony/FE mount"""
        name_lower = name.lower()
        sony_keywords = ['sony', 'fe ', 'vario-tessar', 'za oss', 'g ', 'gm']
        return any(kw in name_lower for kw in sony_keywords)
    
    def scrape_all_pages(self) -> List[Dict]:
        """Navigate through all pages and collect data"""
        self.setup()
        
        try:
            print(f"Loading {self.BASE_URL}...")
            self.page.goto(self.BASE_URL, wait_until='networkidle')
            time.sleep(2)
            
            all_lenses = []
            seen_names = set()
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n--- Page {page_num} ---")
                
                # Get data from current page
                page_data = self.extract_table_data()
                print(f"Found {len(page_data)} rows")
                
                if not page_data:
                    break
                
                # Add new unique lenses
                new_count = 0
                for lens in page_data:
                    if lens['lens_name'] and lens['lens_name'] not in seen_names:
                        seen_names.add(lens['lens_name'])
                        all_lenses.append(lens)
                        new_count += 1
                        print(f"  + {lens['lens_name'][:50]}")
                
                print(f"Added {new_count} new unique lenses")
                
                # Try to go to next page
                try:
                    # Find next page button
                    next_btn = self.page.locator('button:has-text("Go to next page")')
                    
                    if next_btn.count() == 0:
                        print("No next button found - finished")
                        break
                    
                    # Check if disabled
                    if next_btn.is_disabled():
                        print("Next button disabled - finished")
                        break
                    
                    # Click next
                    print("Clicking next page...")
                    next_btn.click()
                    time.sleep(2)
                    page_num += 1
                    
                except Exception as e:
                    print(f"Navigation ended: {e}")
                    break
            
            # Filter Sony lenses
            sony_lenses = [l for l in all_lenses if self.is_sony_lens(l['lens_name'])]
            
            print(f"\n{'='*60}")
            print(f"Total lenses scraped: {len(all_lenses)}")
            print(f"Sony lenses found: {len(sony_lenses)}")
            print(f"{'='*60}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close()
    
    def save_json(self, filepath: str):
        """Save to JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {filepath}")
    
    def save_csv(self, filepath: str):
        """Save to CSV"""
        if not self.lenses:
            print("No data to save")
            return
        
        fields = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                 'year', 'min_focus_distance', 'max_magnification', 'weight',
                 'weight_class', 'length', 'aperture_ring', 'autofocus',
                 'category', 'macro', 'price']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.lenses)
        print(f"Saved to: {filepath}")


def main():
    print("="*60)
    print("Sony Lens Scraper for lab174.com")
    print("="*60)
    
    scraper = Lab174SonyScraper()
    
    try:
        lenses = scraper.scrape_all_pages()
        
        if lenses:
            scraper.save_json('sony_lenses.json')
            scraper.save_csv('sony_lenses.csv')
            
            print("\n" + "="*60)
            print("Sample Sony Lenses:")
            print("="*60)
            for i, lens in enumerate(lenses[:5], 1):
                print(f"\n{i}. {lens['lens_name']}")
                print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
                print(f"   Aperture: f/{lens['f_stop']}")
                print(f"   Weight: {lens['weight']}")
                print(f"   Price: {lens['price']}")
        else:
            print("No Sony lenses found!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
