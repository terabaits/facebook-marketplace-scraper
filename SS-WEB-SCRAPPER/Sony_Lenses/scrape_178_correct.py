"""
Scrape ALL 178 Sony E-mount lenses (all brands)
Properly toggles OFF the Sony brand filter
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_all_178():
    """Scrape all 178 Sony E-mount lenses from all brands"""
    
    print("="*70)
    print("Scraping ALL 178 Sony E-mount lenses")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/3] Loading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            print("\n[2/3] Managing filters...")
            
            # Get initial result count
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                initial = results.inner_text()
                print(f"  Initial: {initial}")
            
            # Toggle OFF Sony brand filter (if active)
            sony_btn = page.get_by_role('button', name='Sony', exact=True)
            if sony_btn.count() > 0:
                pressed = sony_btn.evaluate('el => el.getAttribute("aria-pressed")')
                print(f"  Sony filter active: {pressed}")
                
                if pressed == "true":
                    print("  Toggling Sony filter OFF...")
                    sony_btn.click()
                    time.sleep(3)
                    
                    # Check new count
                    if results.count() > 0:
                        after = results.inner_text()
                        print(f"  After toggle: {after}")
            
            # Also toggle OFF Prime filter (if active)
            prime_btn = page.get_by_role('button', name='Prime', exact=True)
            if prime_btn.count() > 0:
                pressed = prime_btn.evaluate('el => el.getAttribute("aria-pressed")')
                if pressed == "true":
                    print("  Toggling Prime filter OFF...")
                    prime_btn.click()
                    time.sleep(2)
            
            # Also toggle OFF Zoom filter (if active)
            zoom_btn = page.get_by_role('button', name='Zoom', exact=True)
            if zoom_btn.count() > 0:
                pressed = zoom_btn.evaluate('el => el.getAttribute("aria-pressed")')
                if pressed == "true":
                    print("  Toggling Zoom filter OFF...")
                    zoom_btn.click()
                    time.sleep(2)
            
            # Check final result count
            if results.count() > 0:
                final = results.inner_text()
                print(f"\n  Final: {final}")
            
            print("\n[3/3] Extracting lenses...")
            
            page_num = 1
            while page_num <= 10:
                print(f"\n  Page {page_num}:")
                
                # Get pagination info
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"    Range: {page_text}")
                except:
                    pass
                
                # Extract rows using JavaScript
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
                    }).filter(r => r !== null);
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
                        print("    No more pages")
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


def save_files(lenses):
    """Save to files"""
    if not lenses:
        return
    
    # Filter Sony brand lenses
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony brand lenses: {len(sony)}")
    print(f"Other brands: {len(lenses) - len(sony)}")
    
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
        json.dump(sony, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    if sony:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony[0].keys())
            writer.writeheader()
            writer.writerows(sony)
        print("[SAVED] sony_lenses.csv")


def main():
    """Main"""
    try:
        lenses = scrape_all_178()
        
        if lenses:
            save_files(lenses)
            
            sony_count = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total Sony E-mount lenses: {len(lenses)}")
            print(f"Sony brand lenses: {sony_count}")
            print(f"Third-party lenses: {len(lenses) - sony_count}")
            print(f"\nFiles created:")
            print("  - all_lenses.json (all 178 lenses)")
            print("  - all_lenses.csv (all 178 lenses)")
            print("  - sony_lenses.json (Sony brand only)")
            print("  - sony_lenses.csv (Sony brand only)")
            print("="*70)
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
