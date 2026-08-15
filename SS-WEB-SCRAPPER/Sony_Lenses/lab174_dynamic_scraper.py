"""
Sony Lens Scraper for lab174.com - Dynamic/JS-enabled scraper
Uses Playwright for JavaScript-rendered content with pagination
"""

import json
import csv
import time
import re
from pathlib import Path
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright


class Lab174DynamicScraper:
    """Scraper for lab174.com using Playwright for JavaScript-rendered content"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.page = None
        
    def setup_browser(self):
        """Setup Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        print("Playwright browser initialized")
    
    def close_browser(self):
        """Close the browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_data_from_page(self) -> List[Dict]:
        """Extract lens data from current page"""
        page_lenses = []
        
        # Wait for table to be present
        self.page.wait_for_selector('table', timeout=10000)
        
        # Get all rows from the table
        rows = self.page.query_selector_all('table tr')
        
        # Skip header row (first row)
        for row in rows[1:]:
            try:
                cells = row.query_selector_all('td')
                if len(cells) >= 14:
                    lens_data = {
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
                    page_lenses.append(lens_data)
            except Exception as e:
                continue
        
        return page_lenses
    
    def is_sony_lens(self, lens_name: str) -> bool:
        """Check if lens is a Sony lens"""
        name_lower = lens_name.lower()
        sony_indicators = ['sony', 'fe ', 'e ', 'vario-tessar', 'za ', 'g ', 'gm']
        return any(indicator in name_lower for indicator in sony_indicators)
    
    def change_rows_per_page(self, count: int = 100):
        """Try to change rows per page to get more data at once"""
        try:
            # Look for rows per page dropdown/button
            select = self.page.query_selector('text=Rows per page')
            if select:
                print(f"Found rows per page selector")
        except:
            pass
    
    def scrape_all_lenses(self) -> List[Dict]:
        """Scrape all lens data across all pages"""
        self.setup_browser()
        
        try:
            print(f"Loading {self.BASE_URL}...")
            self.page.goto(self.BASE_URL)
            
            # Wait for page to load
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # Extra wait for JavaScript
            
            all_lenses = []
            seen_names = set()  # Track seen lenses to avoid duplicates
            page_num = 1
            
            while True:
                print(f"Processing page {page_num}...")
                
                # Extract data from current page
                page_lenses = self.extract_data_from_page()
                print(f"  Found {len(page_lenses)} lenses on this page")
                
                if not page_lenses:
                    break
                
                # Add unique lenses
                new_count = 0
                for lens in page_lenses:
                    if lens['lens_name'] not in seen_names:
                        seen_names.add(lens['lens_name'])
                        all_lenses.append(lens)
                        new_count += 1
                
                print(f"  {new_count} new unique lenses added")
                
                # Try to click next page button
                try:
                    # Look for next button
                    next_button = self.page.query_selector('button:has-text("next page")')
                    
                    if not next_button:
                        # Try alternative selectors
                        next_button = self.page.query_selector('[aria-label*="next"]')
                    
                    if next_button:
                        # Check if disabled
                        is_disabled = next_button.is_disabled() if hasattr(next_button, 'is_disabled') else False
                        if is_disabled:
                            print("Next button is disabled - reached last page")
                            break
                        
                        # Click and wait
                        print("  Clicking next page...")
                        next_button.click()
                        time.sleep(2)  # Wait for page to load
                        page_num += 1
                    else:
                        print("  No next button found - may be last page")
                        break
                        
                except Exception as e:
                    print(f"  Navigation error: {e}")
                    break
            
            # Filter for Sony lenses only
            sony_lenses = [lens for lens in all_lenses if self.is_sony_lens(lens['lens_name'])]
            
            print(f"\nTotal lenses found: {len(all_lenses)}")
            print(f"Sony lenses found: {len(sony_lenses)}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close_browser()
    
    def save_to_json(self, filepath: str):
        """Save lens data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.lenses)} lenses to {filepath}")
    
    def save_to_csv(self, filepath: str):
        """Save lens data to CSV file"""
        if not self.lenses:
            print("No data to save")
            return
        
        fieldnames = [
            'lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
            'year', 'min_focus_distance', 'max_magnification', 'weight',
            'weight_class', 'length', 'aperture_ring', 'autofocus',
            'category', 'macro', 'price'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.lenses)
        print(f"Saved {len(self.lenses)} lenses to {filepath}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("Sony Lens Scraper for lab174.com (Playwright)")
    print("=" * 60)
    
    try:
        scraper = Lab174DynamicScraper()
        lenses = scraper.scrape_all_lenses()
        
        if lenses:
            # Save to both JSON and CSV
            scraper.save_to_json('sony_lenses_playwright.json')
            scraper.save_to_csv('sony_lenses_playwright.csv')
            
            print("\n" + "=" * 60)
            print(f"Scraping complete! Found {len(lenses)} Sony lenses")
            print("=" * 60)
            
            # Print first few lenses as sample
            print("\nSample data:")
            for i, lens in enumerate(lenses[:5]):
                print(f"\n{i+1}. {lens['lens_name']}")
                print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
                print(f"   Aperture: f/{lens['f_stop']}")
                print(f"   Price: {lens['price']}")
        else:
            print("No lenses found!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
