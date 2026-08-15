"""
Sony Lens Scraper for lab174.com - Complete Implementation
Uses JavaScript evaluation to access the underlying data
"""

import json
import csv
import time
from typing import List, Dict

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class Lab174CompleteScraper:
    """Complete scraper for lab174.com"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.page = None
    
    def setup_browser(self):
        """Setup browser"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright required: pip install playwright")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = context.new_page()
        print("Browser ready")
    
    def close_browser(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_via_javascript(self) -> List[Dict]:
        """Extract all lens data using JavaScript evaluation"""
        
        # JavaScript to extract all data from the table
        script = """
        () => {
            const table = document.querySelector('table');
            if (!table) return [];
            
            const rows = table.querySelectorAll('tbody tr, tr');
            const data = [];
            
            // Skip header row
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const cells = row.querySelectorAll('td');
                if (cells.length >= 14) {
                    data.push({
                        lens_name: cells[0]?.innerText?.trim() || '',
                        focal_length_wide: cells[1]?.innerText?.trim() || '',
                        focal_length_tele: cells[2]?.innerText?.trim() || '',
                        f_stop: cells[3]?.innerText?.trim() || '',
                        year: cells[4]?.innerText?.trim() || '',
                        min_focus_distance: cells[5]?.innerText?.trim() || '',
                        max_magnification: cells[6]?.innerText?.trim() || '',
                        weight: cells[7]?.innerText?.trim() || '',
                        weight_class: cells[8]?.innerText?.trim() || '',
                        length: cells[9]?.innerText?.trim() || '',
                        aperture_ring: cells[10]?.innerText?.trim() || '',
                        autofocus: cells[11]?.innerText?.trim() || '',
                        category: cells[12]?.innerText?.trim() || '',
                        macro: cells[13]?.innerText?.trim() || '',
                        price: cells[14]?.innerText?.trim() || ''
                    });
                }
            }
            return data;
        }
        """
        
        return self.page.evaluate(script)
    
    def navigate_through_pages(self) -> List[Dict]:
        """Navigate through all pages and collect data"""
        all_lenses = []
        seen_names = set()
        
        self.page.goto(self.BASE_URL, wait_until='networkidle')
        time.sleep(2)
        
        page_num = 1
        max_attempts = 10
        
        while page_num <= max_attempts:
            print(f"Processing page {page_num}...")
            
            # Extract data
            page_data = self.extract_via_javascript()
            print(f"  Found {len(page_data)} lenses")
            
            new_count = 0
            for lens in page_data:
                if lens['lens_name'] and lens['lens_name'] not in seen_names:
                    seen_names.add(lens['lens_name'])
                    all_lenses.append(lens)
                    new_count += 1
            
            print(f"  Added {new_count} new lenses")
            
            # Try to find next button
            try:
                # Multiple selector attempts
                next_btn = self.page.locator('button[aria-label*="next"]').or_(
                    self.page.locator('button:has-text("next")')
                ).or_(
                    self.page.locator('button:has-text("›")')
                )
                
                if next_btn.count() > 0:
                    # Check if disabled
                    if next_btn.is_disabled():
                        print("  Next button disabled - done")
                        break
                    
                    # Click
                    next_btn.click()
                    time.sleep(2)
                    page_num += 1
                else:
                    print("  No next button found")
                    break
                    
            except Exception as e:
                print(f"  Navigation complete: {e}")
                break
        
        return all_lenses
    
    def is_sony_lens(self, name: str) -> bool:
        """Check if Sony lens"""
        name_lower = name.lower()
        return any(k in name_lower for k in ['sony', 'fe ', 'vario-tessar', 'za oss'])
    
    def scrape(self) -> List[Dict]:
        """Main scrape method"""
        self.setup_browser()
        
        try:
            all_lenses = self.navigate_through_pages()
            
            # Filter Sony lenses
            sony_lenses = [l for l in all_lenses if self.is_sony_lens(l['lens_name'])]
            
            print(f"\nTotal: {len(all_lenses)} | Sony: {len(sony_lenses)}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close_browser()
    
    def save_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved JSON: {path}")
    
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
        print(f"Saved CSV: {path}")


def main():
    print("=" * 60)
    print("Lab174 Sony Lens Scraper")
    print("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("Install Playwright: pip install playwright")
        print("Then: playwright install chromium")
        return
    
    scraper = Lab174CompleteScraper()
    
    try:
        lenses = scraper.scrape()
        
        if lenses:
            scraper.save_json('sony_lenses.json')
            scraper.save_csv('sony_lenses.csv')
            
            print("\nSample:")
            for i, l in enumerate(lenses[:3], 1):
                print(f"{i}. {l['lens_name']} - {l['price']}")
        else:
            print("No Sony lenses found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
