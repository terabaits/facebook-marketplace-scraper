"""
Complete Sony Lens Scraper for lab174.com
Handles filters properly to capture ALL 178 lenses
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_all_lenses():
    """Scrape all 178 lenses by properly handling filters"""
    
    print("="*70)
    print("Complete Lens Scraper - lab174.com")
    print("="*70)
    
    all_lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/3] Loading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            print("\n[2/3] Resetting filters to show all lenses...")
            
            # Click "All" for Brand filter (first "All" button)
            brand_all = page.locator('button:has-text("All")').nth(0)
            if brand_all.count() > 0:
                print("  Clicking Brand 'All'...")
                brand_all.click()
                time.sleep(2)
            
            # Click "All" for Category filter (second "All" button)
            cat_all = page.locator('button:has-text("All")').nth(1)
            if cat_all.count() > 0:
                print("  Clicking Category 'All'...")
                cat_all.click()
                time.sleep(2)
            
            # Wait for table to update
            page.wait_for_selector('table tbody tr')
            time.sleep(2)
            
            print("\n[3/3] Extracting lenses...")
            
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n  Page {page_num}:")
                
                # Get rows
                rows = page.query_selector_all('table tbody tr')
                print(f"    Found {len(rows)} rows")
                
                new_count = 0
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) >= 14:
                            name = cells[0].inner_text().strip()
                            
                            if name and name not in seen:
                                seen.add(name)
                                all_lenses.append({
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
                
                print(f"    Added {new_count} new lenses (Total: {len(all_lenses)})")
                
                # Check for next page
                try:
                    next_btn = page.query_selector('button[aria-label="Go to next page"]')
                    if not next_btn:
                        print("    No next button")
                        break
                    if next_btn.is_disabled():
                        print("    Next button disabled - done")
                        break
                    
                    print("    Going to next page...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"    Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(all_lenses)} lenses extracted")
            print(f"{'='*70}")
            
            return all_lenses
            
        finally:
            browser.close()


def save_files(lenses):
    """Save to all formats"""
    
    if not lenses:
        print("No lenses to save")
        return
    
    # Filter Sony lenses
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony lenses found: {len(sony)}")
    
    # Save all JSON
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # Save all CSV
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
            
            # Summary
            sony_count = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
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
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
