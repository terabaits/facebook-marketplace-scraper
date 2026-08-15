"""
Scrape using JavaScript evaluation to get all data at once
"""

import json
import csv
from playwright.sync_api import sync_playwright


def scrape_with_js():
    """Scrape using JavaScript"""
    
    print("="*70)
    print("Scraping with JavaScript evaluation")
    print("="*70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\nLoading page...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            print("\nExtracting data via JavaScript...")
            
            # JavaScript to extract all table data
            js_code = """
            () => {
                const rows = document.querySelectorAll('table tbody tr');
                const data = [];
                
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 14) {
                        data.push({
                            lens_name: cells[0]?.innerText?.trim() || '',
                            focal_length_wide: cells[1]?.innerText?.trim() || '',
                            focal_length_tele: cells[2]?.innerText?.trim() || '',
                            f_stop: cells[3]?.innerText?.trim() || '',
                            year: cells[4]?.innerText?.trim() || '',
                            min_focus_distance: cells[5]?.innerText?.trim() || '',
                            max_magnification: cells[6]?.innerText?.trim() || '',
                            weight: cells[7]?.innerText?.trim() || '',
                            weight_class: cells[8]?.innerText?.trim() || '',
                            length: cells[9]?.innerText?.trim() || '',
                            aperture_ring: cells[10]?.innerText?.trim() || '',
                            autofocus: cells[11]?.innerText?.trim() || '',
                            category: cells[12]?.innerText?.trim() || '',
                            macro: cells[13]?.innerText?.trim() || '',
                            price: cells[14]?.innerText?.trim() || ''
                        });
                    }
                });
                
                return data;
            }
            """
            
            lenses = page.evaluate(js_code)
            
            print(f"Extracted {len(lenses)} lenses from current page")
            
            # Navigate through all pages
            all_lenses = []
            seen = set()
            page_num = 1
            
            while page_num <= 10:
                print(f"\nPage {page_num}: {len(lenses)} rows")
                
                new_count = 0
                for lens in lenses:
                    if lens['lens_name'] and lens['lens_name'] not in seen:
                        seen.add(lens['lens_name'])
                        all_lenses.append(lens)
                        new_count += 1
                
                print(f"  New unique: {new_count} (Total: {len(all_lenses)})")
                
                # Try next page
                try:
                    has_next = page.evaluate('() => document.querySelector(\'button[aria-label="Go to next page"]\')?.disabled === false')
                    
                    if not has_next:
                        print("  No more pages")
                        break
                    
                    # Click next
                    page.click('button[aria-label="Go to next page"]')
                    page.wait_for_timeout(3000)
                    
                    # Get new data
                    lenses = page.evaluate(js_code)
                    page_num += 1
                    
                except Exception as e:
                    print(f"  Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(all_lenses)} lenses")
            print(f"{'='*70}")
            
            return all_lenses
            
        finally:
            browser.close()


def save(lenses):
    """Save"""
    if not lenses:
        return
    
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony brand: {len(sony)}")
    
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
        lenses = scrape_with_js()
        if lenses:
            save(lenses)
            
            sony = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print(f"\n{'='*70}")
            print(f"Total: {len(lenses)}")
            print(f"Sony: {sony}")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
