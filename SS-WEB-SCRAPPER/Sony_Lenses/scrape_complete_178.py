"""
Complete Sony Lens Scraper - ALL 178 lenses
Toggles OFF Sony brand filter to show all manufacturers
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def scrape_complete():
    """Scrape all 178 Sony E-mount lenses from all brands"""
    
    print("="*70)
    print("Complete Sony E-mount Lens Scraper")
    print("Capturing all 178 lenses from all manufacturers")
    print("="*70)
    
    lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/3] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            print("\n[2/3] Managing filters...")
            
            # Get initial state
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                initial = results.inner_text()
                print(f"  Current: {initial}")
            
            # The Sony brand button is currently pressed (showing only Sony lenses)
            # We need to find and click it to toggle OFF
            # Use first() to handle multiple matches
            sony_btn = page.locator('button:has-text("Sony")').first
            if sony_btn.count() > 0:
                is_pressed = sony_btn.evaluate('el => el.getAttribute("aria-pressed")')
                print(f"  Sony brand filter active: {is_pressed}")
                
                if is_pressed == "true":
                    print("  Toggling OFF Sony brand filter...")
                    sony_btn.click()
                    time.sleep(3)
                    
                    # Check new count
                    if results.count() > 0:
                        after = results.inner_text()
                        print(f"  After toggle: {after}")
            
            # Also check Prime/Zoom filters
            prime_btn = page.locator('button:has-text("Prime")').first
            if prime_btn.count() > 0:
                pressed = prime_btn.evaluate('el => el.getAttribute("aria-pressed")')
                if pressed == "true":
                    print("  Toggling OFF Prime filter...")
                    prime_btn.click()
                    time.sleep(2)
            
            zoom_btn = page.locator('button:has-text("Zoom")').first
            if zoom_btn.count() > 0:
                pressed = zoom_btn.evaluate('el => el.getAttribute("aria-pressed")')
                if pressed == "true":
                    print("  Toggling OFF Zoom filter...")
                    zoom_btn.click()
                    time.sleep(2)
            
            # Check final result count
            if results.count() > 0:
                final = results.inner_text()
                print(f"\n  Final result count: {final}")
            
            print("\n[3/3] Extracting all lenses...")
            
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n  Page {page_num}:")
                
                # Get pagination info
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"    Range: {page_text}")
                except:
                    pass
                
                # Extract all rows using JavaScript
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
                print(f"    Rows found: {len(rows)}")
                
                new_count = 0
                for row in rows:
                    if row['lens_name'] and row['lens_name'] not in seen:
                        seen.add(row['lens_name'])
                        lenses.append(row)
                        new_count += 1
                
                print(f"    New unique: {new_count} (Total: {len(lenses)})")
                
                # Navigate to next page
                try:
                    has_next = page.evaluate('() => {' +
                        'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                        'return btn && !btn.disabled;' +
                    '}')
                    
                    if not has_next:
                        print("    No more pages")
                        break
                    
                    print("    Going to next page...")
                    page.click('button[aria-label="Go to next page"]')
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"    Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE: {len(lenses)} lenses extracted")
            print(f"{'='*70}")
            
            return lenses
            
        finally:
            browser.close()


def save_data(lenses):
    """Save data to JSON and CSV files"""
    
    if not lenses:
        print("No lenses to save")
        return
    
    # Filter Sony brand lenses
    sony_lenses = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nBreakdown:")
    print(f"  Sony brand lenses: {len(sony_lenses)}")
    print(f"  Third-party lenses: {len(lenses) - len(sony_lenses)}")
    
    # Save all lenses
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony brand lenses
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
    """Main entry point"""
    try:
        lenses = scrape_complete()
        
        if lenses:
            save_data(lenses)
            
            sony_count = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total Sony E-mount lenses: {len(lenses)}")
            print(f"Sony brand lenses: {sony_count}")
            print(f"Third-party lenses: {len(lenses) - sony_count}")
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
