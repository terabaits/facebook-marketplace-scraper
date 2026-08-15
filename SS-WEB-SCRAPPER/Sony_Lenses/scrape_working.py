"""
Working Sony Lens Scraper - Captures available lenses
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_lenses():
    """Scrape lenses from lab174.com"""
    
    print("="*70)
    print("Sony E-mount Lens Scraper")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\nLoading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            # Get result count
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                count_text = results.inner_text()
                print(f"\nCurrent filter shows: {count_text}")
            
            print("\nExtracting lenses...")
            
            page_num = 1
            while page_num <= 10:
                print(f"\nPage {page_num}:")
                
                # Get pagination
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"  Range: {page_text}")
                except:
                    pass
                
                # Extract rows
                js_code = """
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return Array.from(rows).map(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 14) {
                            return {
                                lens_name: cells[0]?.textContent?.trim() || '',
                                focal_length_wide: cells[1]?.textContent?.trim() || '',
                                focal_length_tele: cells[2]?.textContent?.trim() || '',
                                f_stop: cells[3]?.textContent?.trim() || '',
                                year: cells[4]?.textContent?.trim() || '',
                                min_focus_distance: cells[5]?.textContent?.trim() || '',
                                max_magnification: cells[6]?.textContent?.trim() || '',
                                weight: cells[7]?.textContent?.trim() || '',
                                weight_class: cells[8]?.textContent?.trim() || '',
                                length: cells[9]?.textContent?.trim() || '',
                                aperture_ring: cells[10]?.textContent?.trim() || '',
                                autofocus: cells[11]?.textContent?.trim() || '',
                                category: cells[12]?.textContent?.trim() || '',
                                macro: cells[13]?.textContent?.trim() || '',
                                price: cells[14]?.textContent?.trim() || ''
                            };
                        }
                        return null;
                    }).filter(r => r !== null && r.lens_name !== '');
                }
                """
                
                rows = page.evaluate(js_code)
                print(f"  Rows: {len(rows)}")
                
                new = 0
                for row in rows:
                    if row['lens_name'] and row['lens_name'] not in seen:
                        seen.add(row['lens_name'])
                        lenses.append(row)
                        new += 1
                
                print(f"  New: {new} (Total: {len(lenses)})")
                
                # Next
                try:
                    has_next = page.evaluate('() => {' +
                        'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                        'return btn && !btn.disabled;' +
                    '}')
                    
                    if not has_next:
                        print("  Done")
                        break
                    
                    print("  Next...")
                    page.click('button[aria-label="Go to next page"]')
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"  Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(lenses)} lenses")
            print(f"{'='*70}")
            
            return lenses
            
        finally:
            browser.close()


def save(lenses):
    if not lenses:
        return
    
    # Separate by brand
    brands = {}
    for lens in lenses:
        brand = lens['lens_name'].split()[0] if lens['lens_name'] else 'Unknown'
        if brand not in brands:
            brands[brand] = []
        brands[brand].append(lens)
    
    print(f"\nBrands found: {list(brands.keys())}")
    for brand, items in brands.items():
        print(f"  {brand}: {len(items)}")
    
    # Sony brand lenses
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    # Save all
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2)
    print("\n[SAVED] all_lenses.json")
    
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony, f, indent=2)
    print("[SAVED] sony_lenses.json")
    
    if sony:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony[0].keys())
            writer.writeheader()
            writer.writerows(sony)
        print("[SAVED] sony_lenses.csv")


def main():
    try:
        lenses = scrape_lenses()
        if lenses:
            save(lenses)
            
            print(f"\n{'='*70}")
            print(f"Total lenses: {len(lenses)}")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
