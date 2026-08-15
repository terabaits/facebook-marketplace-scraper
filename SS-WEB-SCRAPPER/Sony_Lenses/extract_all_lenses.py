"""
Extract ALL 178 lenses from lab174.com
Uses browser automation to navigate through all 6 pages
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def extract_all_lenses():
    """Extract all 178 lenses from lab174.com"""
    
    print("=" * 70)
    print("Extracting ALL 178 lenses from lab174.com")
    print("=" * 70)
    
    all_lenses = []
    seen_names = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for debugging
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\nLoading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            page_num = 1
            
            while page_num <= 10:  # Max 10 pages
                print(f"\n--- Page {page_num} ---")
                
                # Get page info
                page_info = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                print(f"Page info: {page_info}")
                
                # Extract rows
                rows = page.locator('table tbody tr')
                row_count = rows.count()
                print(f"Found {row_count} rows")
                
                for i in range(row_count):
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
                    except:
                        continue
                
                print(f"Total unique lenses: {len(all_lenses)}")
                
                # Try next page
                try:
                    next_btn = page.locator('button[aria-label="Go to next page"]')
                    
                    if next_btn.count() == 0:
                        print("No next button")
                        break
                    
                    is_disabled = next_btn.is_disabled()
                    if is_disabled:
                        print("Next button disabled - done")
                        break
                    
                    print("Clicking next...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(all_lenses)} lenses extracted")
            print(f"{'='*70}")
            
            return all_lenses
            
        finally:
            browser.close()


def save_lenses(lenses):
    """Save to JSON and CSV"""
    
    # Filter Sony lenses
    sony_lenses = [l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()]
    
    # Save all lenses JSON
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # Save all lenses CSV
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony lenses
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
        writer.writeheader()
        writer.writerows(sony_lenses)
    print("[SAVED] sony_lenses.csv")
    
    return len(sony_lenses)


def main():
    """Main"""
    try:
        lenses = extract_all_lenses()
        
        if lenses:
            sony_count = save_lenses(lenses)
            
            print(f"\n{'='*70}")
            print(f"SUMMARY")
            print(f"{'='*70}")
            print(f"Total lenses: {len(lenses)}")
            print(f"Sony lenses: {sony_count}")
            print(f"\nFiles created:")
            print("  - all_lenses.json")
            print("  - all_lenses.csv")
            print("  - sony_lenses.json")
            print("  - sony_lenses.csv")
            print(f"{'='*70}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
