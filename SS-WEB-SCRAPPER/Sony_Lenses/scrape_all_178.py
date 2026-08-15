"""
Scrape ALL 178 lenses from lab174.com
First disables the Sony filter by clicking "All"
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_all_lenses():
    """Scrape all 178 lenses"""
    
    print("="*70)
    print("Scraping ALL 178 lenses from lab174.com")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/3] Loading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(2)
            
            print("\n[2/3] Clicking 'All' to show all lenses...")
            # Click "All" button to disable Sony filter
            all_btn = page.locator('button:has-text("All")').nth(0)
            if all_btn.count() > 0:
                all_btn.click()
                time.sleep(2)
            
            # Wait for table to update
            page.wait_for_selector('table tbody tr')
            time.sleep(2)
            
            page_num = 1
            
            while True:
                print(f"\n[3/3] Page {page_num} - Extracting...")
                
                # Get rows
                rows = page.query_selector_all('table tbody tr')
                print(f"  Found {len(rows)} rows")
                
                new_count = 0
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) >= 14:
                            name = cells[0].inner_text().strip()
                            
                            if name and name not in seen:
                                seen.add(name)
                                lenses.append({
                                    'lens_name': name,
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
                                })
                                new_count += 1
                    except:
                        pass
                
                print(f"  Added: {new_count} (Total: {len(lenses)})")
                
                # Next page
                try:
                    btn = page.query_selector('button[aria-label="Go to next page"]')
                    if not btn or btn.is_disabled():
                        break
                    btn.click()
                    time.sleep(3)
                    page_num += 1
                    if page_num > 10:
                        break
                except:
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(lenses)} lenses extracted")
            print(f"{'='*70}")
            
            return lenses
            
        finally:
            browser.close()


def save_files(lenses):
    """Save to all formats"""
    
    # Get Sony lenses
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony lenses: {len(sony)}")
    
    # Save all JSON
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # Save all CSV
    if lenses:
        with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
            writer.writeheader()
            writer.writerows(lenses)
        print("[SAVED] all_lenses.csv")
    
    # Save Sony JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    # Save Sony CSV
    if sony:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony[0].keys())
            writer.writeheader()
            writer.writerows(sony)
        print("[SAVED] sony_lenses.csv")


def main():
    """Main"""
    try:
        lenses = scrape_all_lenses()
        
        if lenses:
            save_files(lenses)
            
            print(f"\n{'='*70}")
            print(f"SUMMARY")
            print(f"{'='*70}")
            print(f"Total lenses: {len(lenses)}")
            print(f"Sony lenses: {len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])}")
            print(f"\nFiles:")
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
