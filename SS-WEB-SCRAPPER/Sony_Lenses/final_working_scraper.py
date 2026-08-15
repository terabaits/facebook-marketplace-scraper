"""
Final Working Sony E-mount Lens Scraper
Properly extracts all lens data including full names
"""

import json
import csv
import time
import os
from playwright.sync_api import sync_playwright


def scrape_lenses_final():
    """Scrape lenses with proper data extraction"""
    
    print("="*70)
    print("Final Sony E-mount Lens Scraper")
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
            
            # Get result count
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                count_text = results.inner_text()
                print(f"\n  Current: {count_text}")
            
            print("\n[2/2] Extracting...")
            
            page_num = 1
            while page_num <= 10:
                print(f"\n  Page {page_num}:")
                
                # Get pagination
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"    Range: {page_text}")
                except:
                    pass
                
                # Use Playwright's built-in methods to extract data
                rows = page.locator('table tbody tr')
                row_count = rows.count()
                print(f"    Rows: {row_count}")
                
                new_count = 0
                for i in range(row_count):
                    try:
                        row = rows.nth(i)
                        cells = row.locator('td')
                        
                        if cells.count() >= 14:
                            # Get full text from each cell
                            lens_name = cells.nth(0).inner_text().strip()
                            
                            # Skip if already seen or invalid
                            if not lens_name or lens_name in seen:
                                continue
                            
                            seen.add(lens_name)
                            
                            lens_data = {
                                'lens_name': lens_name,
                                'focal_length_wide': cells.nth(1).inner_text().strip(),
                                'focal_length_tele': cells.nth(2).inner_text().strip(),
                                'f_stop': cells.nth(3).inner_text().strip(),
                                'year': cells.nth(4).inner_text().strip(),
                                'min_focus_distance': cells.nth(5).inner_text().strip(),
                                'max_magnification': cells.nth(6).inner_text().strip(),
                                'weight': cells.nth(7).inner_text().strip(),
                                'weight_class': cells.nth(8).inner_text().strip(),
                                'length': cells.nth(9).inner_text().strip(),
                                'aperture_ring': cells.nth(10).inner_text().strip(),
                                'autofocus': cells.nth(11).inner_text().strip(),
                                'category': cells.nth(12).inner_text().strip(),
                                'macro': cells.nth(13).inner_text().strip(),
                                'price': cells.nth(14).inner_text().strip() if cells.count() > 14 else ''
                            }
                            
                            lenses.append(lens_data)
                            new_count += 1
                            
                    except Exception as e:
                        continue
                
                print(f"    New: {new_count} (Total: {len(lenses)})")
                
                # Sample first row
                if lenses and page_num == 1:
                    print(f"    Sample: {lenses[0]['lens_name'][:50]}")
                
                # Next page
                try:
                    has_next = page.evaluate('() => {' +
                        'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                        'return btn && !btn.disabled;' +
                    '}')
                    
                    if not has_next:
                        print("    Done")
                        break
                    
                    print("    Next...")
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


def analyze_brands(lenses):
    """Analyze by brand"""
    brands = ['Sony', 'Sigma', 'Tamron', 'Laowa', 'Samyang', 'Voigtlander']
    brand_counts = {}
    
    for lens in lenses:
        name = lens.get('lens_name', '')
        for brand in brands:
            if brand in name:
                if brand not in brand_counts:
                    brand_counts[brand] = 0
                brand_counts[brand] += 1
                break
    
    return brand_counts


def save_data(lenses):
    """Save data"""
    if not lenses:
        return
    
    output_dir = r'G:\Github\SS-WEB-SCRAPPER\Sony_Lenses'
    
    # Analyze
    brand_counts = analyze_brands(lenses)
    
    # Sony brand
    sony_lenses = [l for l in lenses if any(x in l.get('lens_name', '').lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nBrand breakdown:")
    for brand, count in sorted(brand_counts.items()):
        print(f"  {brand}: {count}")
    
    print(f"\nSaving...")
    
    # Save all
    all_json = os.path.join(output_dir, 'all_lenses_final.json')
    with open(all_json, 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print(f"  [SAVED] all_lenses_final.json ({len(lenses)} lenses)")
    
    all_csv = os.path.join(output_dir, 'all_lenses_final.csv')
    with open(all_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print(f"  [SAVED] all_lenses_final.csv")
    
    # Brand breakdown
    brand_file = os.path.join(output_dir, 'brand_counts.json')
    with open(brand_file, 'w', encoding='utf-8') as f:
        json.dump(brand_counts, f, indent=2)
    print(f"  [SAVED] brand_counts.json")
    
    # Sony brand
    if sony_lenses:
        sony_json = os.path.join(output_dir, 'sony_lenses_final.json')
        with open(sony_json, 'w', encoding='utf-8') as f:
            json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
        print(f"  [SAVED] sony_lenses_final.json ({len(sony_lenses)} lenses)")
        
        sony_csv = os.path.join(output_dir, 'sony_lenses_final.csv')
        with open(sony_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
            writer.writeheader()
            writer.writerows(sony_lenses)
        print(f"  [SAVED] sony_lenses_final.csv")


def main():
    try:
        lenses = scrape_lenses_final()
        
        if lenses:
            save_data(lenses)
            
            brand_counts = analyze_brands(lenses)
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total lenses: {len(lenses)}")
            print(f"\nBy brand:")
            for brand, count in sorted(brand_counts.items()):
                print(f"  {brand}: {count}")
            print(f"\nFiles:")
            print("  - all_lenses_final.json (all lenses)")
            print("  - all_lenses_final.csv (all lenses)")
            print("  - sony_lenses_final.json (Sony brand)")
            print("  - brand_counts.json")
            print("="*70)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
