"""
Sony Lens Scraper - Capture all 178 lenses
Uses Playwright with better page navigation
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_all_lenses():
    """Scrape all lenses from lab174.com"""
    
    print("="*70)
    print("Scraping all 178 lenses from lab174.com")
    print("="*70)
    
    all_lenses = []
    seen_names = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load page
            print("\n[1/2] Loading lab174.com...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            page_num = 1
            
            while True:
                print(f"\n[Page {page_num}] Extracting data...")
                
                # Get table rows
                rows = page.query_selector_all('table tbody tr')
                print(f"  Found {len(rows)} rows")
                
                page_new = 0
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) >= 14:
                            lens_name = cells[0].inner_text().strip()
                            
                            if lens_name and lens_name not in seen_names:
                                seen_names.add(lens_name)
                                
                                lens_data = {
                                    'lens_name': lens_name,
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
                                
                                all_lenses.append(lens_data)
                                page_new += 1
                    except:
                        continue
                
                print(f"  Added {page_new} new lenses (Total: {len(all_lenses)})")
                
                # Check for next button
                try:
                    next_btn = page.query_selector('button[aria-label="Go to next page"]')
                    
                    if not next_btn:
                        print("  No next button - finished")
                        break
                    
                    if next_btn.is_disabled():
                        print("  Next button disabled - finished")
                        break
                    
                    print("  Going to next page...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                    if page_num > 10:
                        break
                        
                except Exception as e:
                    print(f"  Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(all_lenses)} lenses extracted")
            print(f"{'='*70}")
            
            return all_lenses
            
        finally:
            browser.close()


def save_lenses(lenses):
    """Save lenses to files"""
    
    # Filter Sony lenses
    sony_lenses = []
    for lens in lenses:
        name_lower = lens['lens_name'].lower()
        if any(k in name_lower for k in ['sony', 'vario-tessar']):
            sony_lenses.append(lens)
    
    print(f"\nSony lenses found: {len(sony_lenses)}")
    
    # Save all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2)
    print("\n[SAVED] all_lenses.json")
    
    # Save all CSV
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2)
    print("[SAVED] sony_lenses.json")
    
    # Save Sony CSV
    with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
        writer.writeheader()
        writer.writerows(sony_lenses)
    print("[SAVED] sony_lenses.csv")
    
    return len(sony_lenses)


def main():
    """Main"""
    try:
        lenses = scrape_all_lenses()
        
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
