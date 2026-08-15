"""
Multi-Brand Sony E-mount Lens Scraper
Scrapes all 178 lenses by handling each brand separately
"""

import json
import csv
import time
import os
from playwright.sync_api import sync_playwright


# All brands available on lab174.com
BRANDS = ['Sony', 'Sigma', 'Tamron', 'Laowa', 'Samyang', 'Voigtlander']


def scrape_brand(page, brand_name):
    """Scrape lenses for a specific brand"""
    
    print(f"\n  [{brand_name}] Selecting brand...")
    
    # Click on the brand button
    brand_btn = page.locator(f'button.MuiToggleButton-root:has-text("{brand_name}")')
    if brand_btn.count() == 0:
        print(f"    Brand button not found: {brand_name}")
        return []
    
    # Check if already selected
    is_pressed = brand_btn.evaluate('el => el.getAttribute("aria-pressed")')
    
    if is_pressed != "true":
        brand_btn.click()
        time.sleep(2)
    
    # Get result count
    results = page.locator('h4:has-text("Results:")')
    if results.count() > 0:
        count_text = results.inner_text()
        print(f"    {count_text}")
    
    brand_lenses = []
    seen = set()
    page_num = 1
    
    while page_num <= 10:
        # Extract data
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
        
        new_count = 0
        for row in rows:
            if row['lens_name'] and row['lens_name'] not in seen:
                seen.add(row['lens_name'])
                brand_lenses.append(row)
                new_count += 1
        
        print(f"    Page {page_num}: {new_count} new (Total: {len(brand_lenses)})")
        
        # Next page
        try:
            has_next = page.evaluate('() => {' +
                'const btn = document.querySelector(\'button[aria-label="Go to next page"]\');' +
                'return btn && !btn.disabled;' +
            '}')
            
            if not has_next:
                break
            
            page.click('button[aria-label="Go to next page"]')
            time.sleep(2)
            page_num += 1
            
        except:
            break
    
    print(f"    [{brand_name}] Complete: {len(brand_lenses)} lenses")
    
    # Toggle off this brand before moving to next
    if is_pressed != "true":
        # Only toggle off if we turned it on
        brand_btn.click()
        time.sleep(1)
    
    return brand_lenses


def scrape_all_brands():
    """Scrape all brands"""
    
    print("="*70)
    print("Multi-Brand Sony E-mount Lens Scraper")
    print("Scraping all 178 lenses brand by brand")
    print("="*70)
    
    all_lenses = []
    brand_counts = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/2] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            print("\n[2/2] Scraping each brand...")
            
            for brand in BRANDS:
                brand_lenses = scrape_brand(page, brand)
                all_lenses.extend(brand_lenses)
                brand_counts[brand] = len(brand_lenses)
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses: {len(all_lenses)}")
            print("\nBreakdown by brand:")
            for brand, count in brand_counts.items():
                print(f"  {brand}: {count}")
            print(f"{'='*70}")
            
            return all_lenses, brand_counts
            
        finally:
            browser.close()


def save_data(all_lenses, brand_counts):
    """Save all data"""
    
    if not all_lenses:
        print("No lenses to save")
        return
    
    output_dir = r'G:\Github\SS-WEB-SCRAPPER\Sony_Lenses'
    
    # Filter Sony brand
    sony_lenses = [l for l in all_lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSaving files...")
    
    # Save all lenses
    all_json = os.path.join(output_dir, 'all_lenses_complete.json')
    with open(all_json, 'w', encoding='utf-8') as f:
        json.dump(all_lenses, f, indent=2, ensure_ascii=False)
    print(f"  [SAVED] all_lenses_complete.json ({len(all_lenses)} lenses)")
    
    all_csv = os.path.join(output_dir, 'all_lenses_complete.csv')
    with open(all_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_lenses[0].keys())
        writer.writeheader()
        writer.writerows(all_lenses)
    print(f"  [SAVED] all_lenses_complete.csv")
    
    # Save brand breakdown
    brand_json = os.path.join(output_dir, 'brand_breakdown.json')
    with open(brand_json, 'w', encoding='utf-8') as f:
        json.dump(brand_counts, f, indent=2)
    print(f"  [SAVED] brand_breakdown.json")
    
    # Save Sony lenses
    sony_json = os.path.join(output_dir, 'sony_lenses_all.json')
    with open(sony_json, 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print(f"  [SAVED] sony_lenses_all.json ({len(sony_lenses)} lenses)")
    
    sony_csv = os.path.join(output_dir, 'sony_lenses_all.csv')
    with open(sony_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
        writer.writeheader()
        writer.writerows(sony_lenses)
    print(f"  [SAVED] sony_lenses_all.csv")
    
    # Save per-brand files
    for brand in BRANDS:
        brand_lenses = [l for l in all_lenses if l['lens_name'].startswith(brand)]
        if brand_lenses:
            brand_file = os.path.join(output_dir, f'{brand.lower()}_lenses.json')
            with open(brand_file, 'w', encoding='utf-8') as f:
                json.dump(brand_lenses, f, indent=2, ensure_ascii=False)
            print(f"  [SAVED] {brand.lower()}_lenses.json ({len(brand_lenses)} lenses)")


def main():
    """Main"""
    try:
        all_lenses, brand_counts = scrape_all_brands()
        
        if all_lenses:
            save_data(all_lenses, brand_counts)
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total Sony E-mount lenses: {len(all_lenses)}")
            print(f"\nBreakdown:")
            for brand, count in sorted(brand_counts.items()):
                print(f"  {brand}: {count}")
            print(f"\nOutput files:")
            print("  - all_lenses_complete.json (all lenses)")
            print("  - all_lenses_complete.csv (all lenses)")
            print("  - sony_lenses_all.json (Sony brand)")
            print("  - brand_breakdown.json (counts per brand)")
            print("  - {brand}_lenses.json (individual brand files)")
            print("="*70)
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
