"""
Sony Lens Scraper for lab174.com - Production Ready Version
Extracts all Sony lenses from the complete database with pagination handling
"""

import json
import csv
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright


class Lab174SonyLensScraper:
    """
    Complete scraper for Sony lenses from lab174.com
    Handles pagination and extracts complete lens specifications
    """
    
    BASE_URL = "https://lab174.com/lenses/"
    
    # Column mapping from the table
    COLUMNS = [
        'lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
        'year', 'min_focus_distance', 'max_magnification', 'weight',
        'weight_class', 'length', 'aperture_ring', 'autofocus',
        'category', 'macro', 'price'
    ]
    
    def __init__(self):
        self.all_lenses: List[Dict] = []
        self.sony_lenses: List[Dict] = []
        
    def is_sony_lens(self, name: str) -> bool:
        """Check if a lens is Sony/FE mount"""
        name_lower = name.lower()
        sony_keywords = ['sony', 'fe ', 'vario-tessar', 'za oss']
        return any(keyword in name_lower for keyword in sony_keywords)
    
    def scrape(self) -> List[Dict]:
        """Main scrape method - navigates all pages and extracts data"""
        print("=" * 70)
        print("Sony Lens Scraper for lab174.com")
        print("=" * 70)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            try:
                # Load the page
                print("\n[1/2] Loading lab174.com/lenses/...")
                page.goto(self.BASE_URL, wait_until='networkidle')
                time.sleep(2)
                
                all_data = []
                seen_names = set()
                page_num = 1
                
                while page_num <= 10:  # Safety limit
                    print(f"\n[2/2] Processing page {page_num}...")
                    
                    # Extract data from current page
                    rows = page.locator('table tbody tr')
                    row_count = rows.count()
                    
                    if row_count == 0:
                        # Try alternative selector
                        rows = page.locator('table tr')
                        row_count = rows.count()
                        start_idx = 1  # Skip header
                    else:
                        start_idx = 0
                    
                    print(f"      Found {row_count} rows")
                    
                    new_lenses = 0
                    for i in range(start_idx, row_count):
                        try:
                            row = rows.nth(i)
                            cells = row.locator('td')
                            
                            if cells.count() >= 14:
                                lens_data = {
                                    'lens_name': cells.nth(0).inner_text().strip(),
                                    'focal_length_wide': cells.nth(1).inner_text().strip(),
                                    'focal_length_tele': cells.nth(2).inner_text().strip(),
                                    'f_stop': cells.nth(3).inner_text().strip(),
                                    'year': cells.nth(4).inner_text().strip(),
                                    'min_focus_distance': cells.nth(5).inner_text().strip(),
                                    'max_magnification': cells.nth(6).inner_text().strip(),
                                    'weight': cells.nth(7).inner_text().strip(),
                                    'weight_class': cells.nth(8).inner_text().strip(),
                                    'length': cells.nth(9).inner_text().strip(),
                                    'aperture_ring': cells.nth(10).inner_text().strip(),
                                    'autofocus': cells.nth(11).inner_text().strip(),
                                    'category': cells.nth(12).inner_text().strip(),
                                    'macro': cells.nth(13).inner_text().strip(),
                                    'price': cells.nth(14).inner_text().strip() if cells.count() > 14 else '',
                                }
                                
                                if lens_data['lens_name'] and lens_data['lens_name'] not in seen_names:
                                    seen_names.add(lens_data['lens_name'])
                                    all_data.append(lens_data)
                                    new_lenses += 1
                        except Exception as e:
                            continue
                    
                    print(f"      Added {new_lenses} new lenses")
                    
                    # Check for next page button
                    next_btn = page.locator('button:has-text("Go to next page")')
                    if next_btn.count() == 0:
                        print("      No next button found - finished")
                        break
                    
                    if next_btn.is_disabled():
                        print("      Next button disabled - finished")
                        break
                    
                    print("      Navigating to next page...")
                    next_btn.click()
                    time.sleep(2)
                    page_num += 1
                
                # Filter for Sony lenses
                self.all_lenses = all_data
                self.sony_lenses = [l for l in all_data if self.is_sony_lens(l['lens_name'])]
                
                # Print summary
                print("\n" + "=" * 70)
                print("SCRAPING COMPLETE")
                print("=" * 70)
                print(f"Total lenses scraped: {len(self.all_lenses)}")
                print(f"Sony lenses found: {len(self.sony_lenses)}")
                print("=" * 70)
                
                return self.sony_lenses
                
            finally:
                browser.close()
    
    def save_to_json(self, filepath: str = "sony_lenses.json"):
        """Save Sony lenses to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.sony_lenses, f, indent=2, ensure_ascii=False)
        print(f"\nSaved: {filepath}")
    
    def save_to_csv(self, filepath: str = "sony_lenses.csv"):
        """Save Sony lenses to CSV file"""
        if not self.sony_lenses:
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
            writer.writeheader()
            writer.writerows(self.sony_lenses)
        print(f"Saved: {filepath}")
    
    def save_all_lenses_json(self, filepath: str = "all_lenses.json"):
        """Save all lenses to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.all_lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved: {filepath}")
    
    def print_sample(self, count: int = 5):
        """Print sample Sony lenses"""
        print("\n" + "=" * 70)
        print("Sample Sony Lenses:")
        print("=" * 70)
        for i, lens in enumerate(self.sony_lenses[:count], 1):
            print(f"\n{i}. {lens['lens_name']}")
            print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Weight: {lens['weight']}")
            print(f"   Category: {lens['category']}")
            print(f"   Price: {lens['price']}")


def main():
    """Main entry point"""
    scraper = Lab174SonyLensScraper()
    
    try:
        # Scrape all lenses
        lenses = scraper.scrape()
        
        if lenses:
            # Save all output files
            scraper.save_to_json()
            scraper.save_to_csv()
            scraper.save_all_lenses_json()
            
            # Print sample
            scraper.print_sample(10)
            
            print("\n" + "=" * 70)
            print("All files saved successfully!")
            print("=" * 70)
            print("\nOutput files:")
            print("  - sony_lenses.json (Sony lenses in JSON format)")
            print("  - sony_lenses.csv (Sony lenses in CSV format)")
            print("  - all_lenses.json (All lenses from the database)")
            print("=" * 70)
        else:
            print("\nNo Sony lenses found!")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
