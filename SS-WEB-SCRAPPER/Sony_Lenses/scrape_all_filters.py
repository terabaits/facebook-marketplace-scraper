"""
Scrape ALL 178 lenses by properly resetting filters
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_all():
    """Scrape all 178 lenses"""
    
    print("="*70)
    print("Scraping ALL 178 Sony E-mount lenses")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/2] Loading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            # Check current filters
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                initial = results.inner_text()
                print(f"  Starting: {initial}")
            
            # Click "All" for Lens Type (first button group)
            print("\n  Resetting Lens Type filter...")
            all_lens_type = page.locator('button:has-text("All")').nth(0)
            if all_lens_type.count() > 0:
                all_lens_type.click()
                time.sleep(2)
            
            # Click "All" for Brand (second button group)  
            print("  Resetting Brand filter...")
            all_brand = page.locator('button:has-text("All")').nth(1)
            if all_brand.count() > 0:
                all_brand.click()
                time.sleep(2)
            
            # Click "All" for Category (third button group)
            print("  Resetting Category filter...")
            all_cat = page.locator('button:has-text("All")').nth(2)
            if all_cat.count() > 0:
                all_cat.click()
                time.sleep(2)
            
            # Check result count after reset
            if results.count() > 0:
                final = results.inner_text()
                print(f"\n  After reset: {final}")
            
            print("\n[2/2] Extracting lenses...")
            
            page_num = 1
            while page_num <= 10:
                print(f"\n  Page {page_num}:")
                
                # Get pagination
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"    Range: {page_text}")
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
                print(f"    Rows: {len(rows)}")
                
                new = 0
                for row in rows:
                    if row['lens_name'] and row['lens_name'] not in seen:
                        seen.add(row['lens_name'])
                        lenses.append(row)
                        new += 1
                
                print(f"    New: {new} (Total: {len(lenses)})")
                
                # Next page
                try:
                    has_next = page.evaluate('() => {' +
                        'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                        'return btn && !btn.disabled;' +
                    '}')
                    
                    if not has_next:
                        print("    Done")
                        break
                    
                    print("    Next page...")
                    page.click('button[aria-label="Go to next page"]')
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"    Done: {e}")
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
    
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony brand: {len(sony)}")
    print(f"Other brands: {len(lenses) - len(sony)}")
    
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2)
    print("\n[SAVED] all_lenses.json")
    
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
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
        lenses = scrape_all()
        if lenses:
            save(lenses)
            
            sony = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print(f"\n{'='*70}")
            print(f"Total: {len(lenses)}")
            print(f"Sony: {sony}")
            print(f"Third-party: {len(lenses) - sony}")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
