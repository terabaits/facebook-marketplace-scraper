"""
Sony Lens Scraper for lab174.com - Using Playwright with explicit waits
This script scrapes Sony lens data from lab174.com lenses database
"""

import json
import csv
import time
from typing import List, Dict


def is_sony_lens(name: str) -> bool:
    """Check if a lens is a Sony/FE mount lens"""
    name_lower = name.lower()
    sony_keywords = ['sony', 'fe ', 'vario-tessar', 'za oss']
    return any(keyword in name_lower for keyword in sony_keywords)


def scrape_lab174():
    """Scrape all lenses from lab174.com"""
    from playwright.sync_api import sync_playwright
    
    print("Starting lab174.com Sony Lens Scraper...")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Navigate to the page
            print("\n1. Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            all_lenses = []
            seen_names = set()
            page_num = 1
            
            while True:
                print(f"\n2. Processing page {page_num}...")
                
                # Get all rows from the table
                rows = page.locator('table tbody tr')
                count = rows.count()
                
                if count == 0:
                    print("   No rows found, trying alternative selector...")
                    rows = page.locator('table tr')
                    count = rows.count()
                    # Skip header
                    start_idx = 1
                else:
                    start_idx = 0
                
                print(f"   Found {count} rows")
                
                new_lenses = 0
                for i in range(start_idx, count):
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
                                all_lenses.append(lens_data)
                                new_lenses += 1
                    except Exception as e:
                        continue
                
                print(f"   Added {new_lenses} new unique lenses")
                
                # Check for next page button
                next_btn = page.locator('button:has-text("Go to next page")')
                if next_btn.count() == 0:
                    print("   No next button found - finished")
                    break
                
                if next_btn.is_disabled():
                    print("   Next button disabled - finished")
                    break
                
                print("   Clicking next page...")
                next_btn.click()
                time.sleep(3)
                page_num += 1
                
                if page_num > 10:  # Safety limit
                    print("   Reached max pages - stopping")
                    break
            
            print(f"\n{'='*60}")
            print(f"Scraping Complete!")
            print(f"Total lenses: {len(all_lenses)}")
            
            # Filter for Sony lenses
            sony_lenses = [l for l in all_lenses if is_sony_lens(l['lens_name'])]
            print(f"Sony lenses: {len(sony_lenses)}")
            print(f"{'='*60}")
            
            return all_lenses, sony_lenses
            
        finally:
            browser.close()


def save_data(all_lenses: List[Dict], sony_lenses: List[Dict]):
    """Save scraped data to files"""
    
    # Save all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(all_lenses, f, indent=2, ensure_ascii=False)
    print("\nSaved all_lenses.json")
    
    # Save Sony lenses to JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("Saved sony_lenses.json")
    
    # Save Sony lenses to CSV
    if sony_lenses:
        fieldnames = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                     'year', 'min_focus_distance', 'max_magnification', 'weight',
                     'weight_class', 'length', 'aperture_ring', 'autofocus',
                     'category', 'macro', 'price']
        
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("Saved sony_lenses.csv")
    
    # Print sample
    print("\n" + "="*60)
    print("Sample Sony Lenses:")
    print("="*60)
    for i, lens in enumerate(sony_lenses[:5], 1):
        print(f"\n{i}. {lens['lens_name']}")
        print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
        print(f"   Aperture: f/{lens['f_stop']}")
        print(f"   Weight: {lens['weight']}")
        print(f"   Price: {lens['price']}")


def main():
    """Main entry point"""
    try:
        all_lenses, sony_lenses = scrape_lab174()
        save_data(all_lenses, sony_lenses)
        
        print(f"\n{'='*60}")
        print("Scraping Summary:")
        print(f"{'='*60}")
        print(f"Total lenses scraped: {len(all_lenses)}")
        print(f"Sony lenses found: {len(sony_lenses)}")
        print(f"Files saved:")
        print(f"  - all_lenses.json")
        print(f"  - sony_lenses.json")
        print(f"  - sony_lenses.csv")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
