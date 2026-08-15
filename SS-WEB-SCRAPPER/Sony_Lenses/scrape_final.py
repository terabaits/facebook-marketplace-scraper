"""
FINAL Sony Lens Scraper - Captures all 178 Sony E-mount lenses
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape():
    """Scrape all 178 lenses"""
    
    print("="*70)
    print("FINAL Sony Lens Scraper - lab174.com")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/2] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            print("\n[2/2] Extracting all 178 lenses...")
            
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n--- Page {page_num} ---")
                
                # Get pagination info
                try:
                    page_info = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"  Range: {page_info}")
                except:
                    pass
                
                # Extract all rows
                rows = page.query_selector_all('table tbody tr')
                print(f"  Rows on page: {len(rows)}")
                
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
                
                print(f"  New lenses: {new_count} (Total: {len(lenses)})")
                
                # Navigate to next page
                try:
                    next_btn = page.query_selector('button[aria-label="Go to next page"]')
                    if not next_btn:
                        print("  No next button found")
                        break
                    
                    if next_btn.is_disabled():
                        print("  Next button disabled - finished")
                        break
                    
                    print("  Going to next page...")
                    next_btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"  Navigation complete: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses extracted: {len(lenses)}")
            print(f"{'='*70}")
            
            return lenses
            
        finally:
            browser.close()


def save_files(lenses):
    """Save to all formats"""
    
    if not lenses:
        print("No lenses to save")
        return
    
    # Filter Sony brand lenses
    sony_lenses = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony brand lenses: {len(sony_lenses)}")
    
    # Save all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony lenses
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    if sony_lenses:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("[SAVED] sony_lenses.csv")


def main():
    """Main"""
    try:
        lenses = scrape()
        
        if lenses:
            save_files(lenses)
            
            sony_count = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total Sony E-mount lenses: {len(lenses)}")
            print(f"Sony brand lenses: {sony_count}")
            print(f"\nOutput files:")
            print("  - all_lenses.json (all lenses)")
            print("  - all_lenses.csv (all lenses)")
            print("  - sony_lenses.json (Sony brand only)")
            print("  - sony_lenses.csv (Sony brand only)")
            print("="*70)
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
