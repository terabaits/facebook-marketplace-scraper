"""
Sony Lens Scraper for lab174.com - Final Complete Version
Extracts ALL Sony lenses by navigating through all 178 lenses (6 pages)
"""

import json
import csv
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright


def extract_sony_lenses():
    """Extract all Sony lenses from lab174.com across all pages"""
    
    print("=" * 70)
    print("Sony Lens Scraper for lab174.com")
    print("=" * 70)
    
    all_lenses = []
    sony_lenses = []
    seen_names = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load the page
            print("\n[1/2] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            page_num = 1
            
            while True:
                print(f"\n[2/2] Processing page {page_num}...")
                
                # Get all rows from the table
                rows = page.locator('table tbody tr')
                row_count = rows.count()
                
                print(f"      Found {row_count} rows on this page")
                
                new_count = 0
                for i in range(row_count):
                    try:
                        row = rows.nth(i)
                        cells = row.locator('td')
                        
                        if cells.count() >= 14:
                            lens_name = cells.nth(0).inner_text().strip()
                            
                            # Skip if already seen
                            if not lens_name or lens_name in seen_names:
                                continue
                            
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
                            if any(k in name_lower for k in ['sony', 'vario-tessar']):
                                sony_lenses.append(lens_data)
                                new_count += 1
                                
                    except Exception as e:
                        continue
                
                print(f"      Added {new_count} Sony lenses from this page")
                
                # Try to click next page
                try:
                    next_btn = page.locator('button[aria-label="Go to next page"]')
                    
                    if next_btn.count() == 0:
                        print("      No next button found")
                        break
                    
                    if next_btn.is_disabled():
                        print("      Next button disabled - finished")
                        break
                    
                    print("      Navigating to next page...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                    if page_num > 10:  # Safety limit
                        break
                        
                except Exception as e:
                    print(f"      Navigation error: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses scraped: {len(all_lenses)}")
            print(f"Sony lenses found: {len(sony_lenses)}")
            print(f"{'='*70}")
            
            return all_lenses, sony_lenses
            
        finally:
            browser.close()


def save_files(all_lenses, sony_lenses):
    """Save data to JSON and CSV files"""
    
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
        fieldnames = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                     'year', 'min_focus_distance', 'max_magnification', 'weight',
                     'weight_class', 'length', 'aperture_ring', 'autofocus',
                     'category', 'macro', 'price']
        
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("Saved: sony_lenses.csv")


def main():
    """Main entry point"""
    try:
        all_lenses, sony_lenses = extract_sony_lenses()
        save_files(all_lenses, sony_lenses)
        
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
        print("  - all_lenses.json (all 178 lenses)")
        print("  - sony_lenses.json (Sony lenses only)")
        print("  - sony_lenses.csv (Sony lenses in CSV format)")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
