"""
Sony Lens Scraper for lab174.com - Complete Version
Captures ALL 178 lenses across all pages
"""

import json
import csv
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright


def scrape_all_lenses():
    """Scrape all 178 lenses from lab174.com"""
    
    print("=" * 70)
    print("Lab174.com Complete Lens Scraper")
    print("Capturing all 178 lenses across all pages...")
    print("=" * 70)
    
    all_lenses = []
    seen_names = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load page
            print("\n[Step 1] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n[Step 2] Processing page {page_num}...")
                
                # Wait for table
                page.wait_for_selector('table tbody tr', timeout=10000)
                
                # Get all rows
                rows = page.locator('table tbody tr')
                row_count = rows.count()
                
                print(f"  Found {row_count} rows")
                
                new_count = 0
                for i in range(row_count):
                    try:
                        row = rows.nth(i)
                        cells = row.locator('td')
                        cell_count = cells.count()
                        
                        if cell_count >= 14:
                            lens_name = cells.nth(0).inner_text().strip()
                            
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
                                'price': cells.nth(14).inner_text().strip() if cell_count > 14 else '',
                            }
                            
                            all_lenses.append(lens_data)
                            new_count += 1
                            
                    except Exception:
                        continue
                
                print(f"  Added {new_count} lenses (Total: {len(all_lenses)})")
                
                # Try to click next
                try:
                    next_btn = page.locator('button:has-text("Go to next page")')
                    
                    if next_btn.count() == 0:
                        print("  No next button - finished")
                        break
                    
                    is_disabled = next_btn.evaluate('el => el.disabled')
                    if is_disabled:
                        print("  Next disabled - finished")
                        break
                    
                    print("  Clicking next page...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"  Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses: {len(all_lenses)}")
            
            # Filter Sony
            sony_lenses = []
            for lens in all_lenses:
                name_lower = lens['lens_name'].lower()
                if any(k in name_lower for k in ['sony', 'vario-tessar']):
                    sony_lenses.append(lens)
            
            print(f"Sony lenses: {len(sony_lenses)}")
            print(f"{'='*70}")
            
            return all_lenses, sony_lenses
            
        finally:
            browser.close()


def save_files(all_lenses, sony_lenses):
    """Save data to files"""
    
    # JSON - all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(all_lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # CSV - all lenses
    if all_lenses:
        with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_lenses[0].keys())
            writer.writeheader()
            writer.writerows(all_lenses)
        print("[SAVED] all_lenses.csv")
    
    # JSON - Sony lenses
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    # CSV - Sony lenses
    if sony_lenses:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("[SAVED] sony_lenses.csv")


def main():
    """Main entry point"""
    try:
        all_lenses, sony_lenses = scrape_all_lenses()
        save_files(all_lenses, sony_lenses)
        
        print("\n" + "="*70)
        print("Sample Sony Lenses:")
        print("="*70)
        for i, lens in enumerate(sony_lenses[:5], 1):
            print(f"\n{i}. {lens['lens_name']}")
            print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Price: {lens['price']}")
        
        print(f"\n{'='*70}")
        print("OUTPUT FILES:")
        print("  - all_lenses.json (178 lenses)")
        print("  - all_lenses.csv (178 lenses)")
        print("  - sony_lenses.json (Sony only)")
        print("  - sony_lenses.csv (Sony only)")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
