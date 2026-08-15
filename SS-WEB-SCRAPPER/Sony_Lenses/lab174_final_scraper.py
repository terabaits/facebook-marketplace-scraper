"""
Sony Lens Scraper for lab174.com - Final Implementation
Extracts all lens data by simulating browser navigation
"""

import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available. Install with: pip install playwright")
    print("Then run: playwright install")


class Lab174Scraper:
    """Scraper for lab174.com lenses database"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.page = None
    
    def setup_browser(self):
        """Setup Playwright browser"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is required. Run: pip install playwright && playwright install")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = context.new_page()
        print("Browser initialized")
    
    def close_browser(self):
        """Close browser resources"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_current_page_data(self) -> List[Dict]:
        """Extract lens data from the current page"""
        rows_data = []
        
        # Wait for table and get rows
        self.page.wait_for_selector('table tbody tr, table tr', timeout=10000)
        
        # Get all rows (skip header)
        rows = self.page.query_selector_all('table tbody tr')
        if not rows:
            rows = self.page.query_selector_all('table tr')[1:]  # Skip header
        
        for row in rows:
            try:
                cells = row.query_selector_all('td')
                if len(cells) >= 14:
                    row_data = {
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
                    if row_data['lens_name']:  # Only add if has name
                        rows_data.append(row_data)
            except Exception as e:
                continue
        
        return rows_data
    
    def is_sony_lens(self, name: str) -> bool:
        """Check if a lens is a Sony/FE mount lens"""
        name_lower = name.lower()
        sony_keywords = ['sony', 'fe ', 'vario-tessar', 'za oss']
        return any(keyword in name_lower for keyword in sony_keywords)
    
    def scrape_all_lenses(self) -> List[Dict]:
        """Scrape all lenses across all pages"""
        self.setup_browser()
        
        try:
            print(f"Loading {self.BASE_URL}...")
            self.page.goto(self.BASE_URL, wait_until='networkidle')
            time.sleep(2)
            
            all_lenses = []
            seen_names = set()
            page_num = 1
            max_pages = 10  # Safety limit
            
            while page_num <= max_pages:
                print(f"Processing page {page_num}...")
                
                # Extract data from current page
                page_data = self.extract_current_page_data()
                print(f"  Found {len(page_data)} rows")
                
                if not page_data:
                    break
                
                # Add new unique lenses
                new_count = 0
                for lens in page_data:
                    if lens['lens_name'] and lens['lens_name'] not in seen_names:
                        seen_names.add(lens['lens_name'])
                        all_lenses.append(lens)
                        new_count += 1
                
                print(f"  Added {new_count} new unique lenses")
                
                # Try to find and click next page
                try:
                    # Look for the next button
                    next_button = self.page.locator('button:has-text("Go to next page")')
                    
                    if next_button.count() > 0:
                        # Check if disabled
                        is_disabled = next_button.is_disabled()
                        if is_disabled:
                            print("  Next button disabled - reached end")
                            break
                        
                        # Click next
                        print("  Clicking next...")
                        next_button.click()
                        time.sleep(2)
                        page_num += 1
                    else:
                        print("  No next button - done")
                        break
                        
                except Exception as e:
                    print(f"  Navigation ended: {e}")
                    break
            
            # Filter for Sony lenses
            sony_lenses = [lens for lens in all_lenses if self.is_sony_lens(lens['lens_name'])]
            
            print(f"\n{'='*60}")
            print(f"Total lenses: {len(all_lenses)}")
            print(f"Sony lenses: {len(sony_lenses)}")
            print(f"{'='*60}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close_browser()
    
    def save_to_json(self, filepath: str):
        """Save data to JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")
    
    def save_to_csv(self, filepath: str):
        """Save data to CSV"""
        if not self.lenses:
            return
        
        fieldnames = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                     'year', 'min_focus_distance', 'max_magnification', 'weight',
                     'weight_class', 'length', 'aperture_ring', 'autofocus',
                     'category', 'macro', 'price']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.lenses)
        print(f"Saved to {filepath}")


def main():
    print("=" * 60)
    print("Sony Lens Scraper for lab174.com")
    print("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\nPlaywright is not installed.")
        print("Please run: pip install playwright")
        print("Then: playwright install chromium")
        return
    
    scraper = Lab174Scraper()
    
    try:
        lenses = scraper.scrape_all_lenses()
        
        if lenses:
            scraper.save_to_json('sony_lenses.json')
            scraper.save_to_csv('sony_lenses.csv')
            
            print("\nSample Sony lenses:")
            for i, lens in enumerate(lenses[:5], 1):
                print(f"\n{i}. {lens['lens_name']}")
                print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
                print(f"   Aperture: f/{lens['f_stop']}")
                print(f"   Price: {lens['price']}")
        else:
            print("No Sony lenses found!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
