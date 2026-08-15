"""
Simple scraper - just navigate through pages and extract data
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def simple_scrape():
    """Simple scrape"""
    
    print("="*70)
    print("Simple Scraper - lab174.com")
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
            
            print("\nExtracting data...")
            
            page_num = 1
            
            while True:
                print(f"\nPage {page_num}:")
                
                # Get pagination text
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"  Range: {page_text}")
                except:
                    pass
                
                # Get table rows using JavaScript for reliability
                js_get_rows = """
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return Array.from(rows).map(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 14) {
                            return {
                                name: cells[0]?.textContent?.trim() || '',
                                wide: cells[1]?.textContent?.trim() || '',
                                tele: cells[2]?.textContent?.trim() || '',
                                fstop: cells[3]?.textContent?.trim() || '',
                                year: cells[4]?.textContent?.trim() || '',
                                focus: cells[5]?.textContent?.trim() || '',
                                mag: cells[6]?.textContent?.trim() || '',
                                weight: cells[7]?.textContent?.trim() || '',
                                wclass: cells[8]?.textContent?.trim() || '',
                                length: cells[9]?.textContent?.trim() || '',
                                aperture: cells[10]?.textContent?.trim() || '',
                                af: cells[11]?.textContent?.trim() || '',
                                cat: cells[12]?.textContent?.trim() || '',
                                macro: cells[13]?.textContent?.trim() || '',
                                price: cells[14]?.textContent?.trim() || ''
                            };
                        }
                        return null;
                    }).filter(r => r !== null);
                }
                """
                
                rows = page.evaluate(js_get_rows)
                print(f"  Rows found: {len(rows)}")
                
                new = 0
                for row in rows:
                    if row['name'] and row['name'] not in seen:
                        seen.add(row['name'])
                        lenses.append({
                            'lens_name': row['name'],
                            'focal_length_wide': row['wide'],
                            'focal_length_tele': row['tele'],
                            'f_stop': row['fstop'],
                            'year': row['year'],
                            'min_focus_distance': row['focus'],
                            'max_magnification': row['mag'],
                            'weight': row['weight'],
                            'weight_class': row['wclass'],
                            'length': row['length'],
                            'aperture_ring': row['aperture'],
                            'autofocus': row['af'],
                            'category': row['cat'],
                            'macro': row['macro'],
                            'price': row['price']
                        })
                        new += 1
                
                print(f"  New: {new} (Total: {len(lenses)})")
                
                # Next page
                try:
                    has_next = page.evaluate('() => {' +
                        'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                        'return btn && !btn.disabled;' +
                    '}')
                    
                    if not has_next:
                        print("  No more pages")
                        break
                    
                    print("  Clicking next...")
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
        lenses = simple_scrape()
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
