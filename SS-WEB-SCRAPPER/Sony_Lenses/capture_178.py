"""
Capture all 178 lenses from lab174.com
Simply navigates through all pages and extracts data
"""

import json
import csv
import time
from playwright.sync_api import sync_playwright


def capture_all():
    """Capture all lenses"""
    
    print("="*70)
    print("Capturing all 178 lenses from lab174.com")
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
            
            page_num = 1
            
            while page_num <= 10:
                print(f"\n--- Page {page_num} ---")
                
                # Get pagination info
                try:
                    page_info = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"  Pagination: {page_info}")
                except:
                    pass
                
                # Extract rows
                rows = page.query_selector_all('table tbody tr')
                print(f"  Found {len(rows)} rows")
                
                new = 0
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
                                new += 1
                    except:
                        pass
                
                print(f"  Added {new} new lenses (Total: {len(lenses)})")
                
                # Next page
                try:
                    btn = page.query_selector('button[aria-label="Go to next page"]')
                    if not btn:
                        print("  No next button")
                        break
                    if btn.is_disabled():
                        print("  Next button disabled - done")
                        break
                    
                    print("  Clicking next...")
                    btn.click()
                    time.sleep(3)
                    page_num += 1
                    
                except Exception as e:
                    print(f"  Done: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"COMPLETE: {len(lenses)} lenses captured")
            print(f"{'='*70}")
            
            return lenses
            
        finally:
            browser.close()


def save(lenses):
    """Save"""
    if not lenses:
        return
    
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony lenses: {len(sony)}")
    
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
        lenses = capture_all()
        if lenses:
            save(lenses)
            
            sony = len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])
            
            print(f"\n{'='*70}")
            print(f"SUMMARY")
            print(f"{'='*70}")
            print(f"Total lenses: {len(lenses)}")
            print(f"Sony lenses: {sony}")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
