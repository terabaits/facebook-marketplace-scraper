"""
Sony Lens Scraper for lab174.com - Complete Version
Changes "Rows per page" to show all lenses, then extracts all Sony lenses
"""

import json
import csv
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright


def scrape_sony_lenses():
    """Scrape all Sony lenses from lab174.com"""
    
    print("=" * 70)
    print("Sony Lens Scraper for lab174.com")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load page
            print("\n[1/3] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            # Try to change rows per page to maximum
            print("\n[2/3] Attempting to show all rows...")
            
            # Look for rows per page dropdown/button
            rows_per_page = page.locator('text=Rows per page').or_(
                page.locator('[aria-label*="rows per page"]')
            ).or_(
                page.locator('button:has-text("30")')
            )
            
            if rows_per_page.count() > 0:
                print("      Found rows per page control")
                rows_per_page.click()
                time.sleep(1)
                
                # Look for option to show all or high number
                all_option = page.locator('text=All').or_(
                    page.locator('text=100').or_(page.locator('text=250'))
                )
                if all_option.count() > 0:
                    all_option.first.click()
                    print("      Changed to show all rows")
                    time.sleep(2)
            
            # Extract all lens data from the table
            print("\n[3/3] Extracting lens data...")
            
            all_lenses = []
            sony_lenses = []
            seen_names = set()
            
            # Get all rows
            rows = page.locator('table tbody tr')
            if rows.count() == 0:
                rows = page.locator('table tr')
                start_idx = 1
            else:
                start_idx = 0
            
            row_count = rows.count()
            print(f"      Found {row_count} rows in table")
            
            for i in range(start_idx, row_count):
                try:
                    row = rows.nth(i)
                    cells = row.locator('td')
                    
                    if cells.count() >= 14:
                        lens_name = cells.nth(0).inner_text().strip()
                        
                        if lens_name and lens_name not in seen_names:
                            seen_names.add(lens_name)
                            
                            lens_data = {
                                'lens_name': lens_name,
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
                            
                            all_lenses.append(lens_data)
                            
                            # Check if Sony lens
                            name_lower = lens_name.lower()
                            if any(k in name_lower for k in ['sony', 'fe ', 'vario-tessar', 'za oss']):
                                sony_lenses.append(lens_data)
                                
                except Exception as e:
                    continue
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses: {len(all_lenses)}")
            print(f"Sony lenses: {len(sony_lenses)}")
            print(f"{'='*70}")
            
            return all_lenses, sony_lenses
            
        finally:
            browser.close()


def save_data(all_lenses, sony_lenses):
    """Save data to files"""
    
    # Save all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(all_lenses, f, indent=2, ensure_ascii=False)
    print("\nSaved: all_lenses.json")
    
    # Save Sony lenses JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("Saved: sony_lenses.json")
    
    # Save Sony lenses CSV
    if sony_lenses:
        fields = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                 'year', 'min_focus_distance', 'max_magnification', 'weight',
                 'weight_class', 'length', 'aperture_ring', 'autofocus',
                 'category', 'macro', 'price']
        
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("Saved: sony_lenses.csv")


def main():
    """Main entry point"""
    try:
        all_lenses, sony_lenses = scrape_sony_lenses()
        save_data(all_lenses, sony_lenses)
        
        # Print sample
        print("\n" + "="*70)
        print("Sample Sony Lenses:")
        print("="*70)
        for i, lens in enumerate(sony_lenses[:10], 1):
            print(f"\n{i}. {lens['lens_name']}")
            print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Weight: {lens['weight']}")
            print(f"   Price: {lens['price']}")
        
        print(f"\n{'='*70}")
        print("Output files created:")
        print("  - all_lenses.json")
        print("  - sony_lenses.json")
        print("  - sony_lenses.csv")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
