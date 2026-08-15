"""
Fixed Multi-Brand Sony E-mount Lens Scraper
Properly extracts all data with correct column alignment
"""

import json
import csv
import time
import os
import re
from playwright.sync_api import sync_playwright


BRANDS = ['Sony', 'Sigma', 'Tamron', 'Laowa', 'Samyang', 'Voigtlander']


def clean_text(text):
    """Clean up text"""
    if not text:
        return ''
    # Remove extra whitespace and normalize
    return ' '.join(text.split())


def scrape_all_data():
    """Scrape all lens data from the current page view"""
    
    print("="*70)
    print("Sony E-mount Lens Scraper - Complete Dataset")
    print("="*70)
    
    all_lenses = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("\n[1/2] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            # Get result count
            results = page.locator('h4:has-text("Results:")')
            if results.count() > 0:
                count_text = results.inner_text()
                print(f"\n  Current view: {count_text}")
            
            print("\n[2/2] Extracting all lenses...")
            
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                print(f"\n  Page {page_num}:")
                
                # Get pagination
                try:
                    page_text = page.locator('text=/\\d+–\\d+ of \\d+/').inner_text()
                    print(f"    Range: {page_text}")
                except:
                    pass
                
                # Extract using JavaScript with proper parsing
                js_code = """
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const data = [];
                    
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 14) {
                            // Try to get full lens name from the first cell
                            const nameCell = cells[0];
                            const nameText = nameCell.textContent || '';
                            
                            // Extract actual lens name (usually contains brand and model)
                            // The full name is typically in the text content
                            const lensName = nameText.trim().split('\\n')[0].trim();
                            
                            data.push({
                                lens_name: lensName,
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
                            });
                        }
                    });
                    
                    return data;
                }
                """
                
                rows = page.evaluate(js_code)
                print(f"    Rows found: {len(rows)}")
                
                new_count = 0
                for row in rows:
                    # Validate the data - lens_name should contain brand name
                    name = row.get('lens_name', '')
                    
                    # Skip if invalid or duplicate
                    if not name or len(name) < 5 or name in seen:
                        continue
                    
                    # Check if it looks like a valid lens name (contains known brand)
                    is_valid = any(brand in name for brand in BRANDS + ['Laowa', 'Samyang', 'Voigtlander'])
                    
                    if is_valid:
                        seen.add(name)
                        all_lenses.append(row)
                        new_count += 1
                
                print(f"    New unique: {new_count} (Total: {len(all_lenses)})")
                
                # Sample first row for debugging
                if rows and page_num == 1:
                    print(f"    Sample: {rows[0].get('lens_name', 'N/A')[:50]}")
                
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
            print(f"SCRAPING COMPLETE: {len(all_lenses)} lenses")
            print(f"{'='*70}")
            
            return all_lenses
            
        finally:
            browser.close()


def analyze_brands(lenses):
    """Analyze lenses by brand"""
    
    brand_counts = {}
    
    for lens in lenses:
        name = lens.get('lens_name', '')
        
        # Determine brand
        brand = 'Unknown'
        for b in BRANDS:
            if b in name:
                brand = b
                break
        
        if brand not in brand_counts:
            brand_counts[brand] = 0
        brand_counts[brand] += 1
    
    return brand_counts


def save_data(lenses):
    """Save all data"""
    
    if not lenses:
        print("No lenses to save")
        return
    
    output_dir = r'G:\Github\SS-WEB-SCRAPPER\Sony_Lenses'
    
    # Analyze brands
    brand_counts = analyze_brands(lenses)
    
    # Filter Sony brand lenses
    sony_lenses = [l for l in lenses if any(x in l.get('lens_name', '').lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nBrand breakdown:")
    for brand, count in sorted(brand_counts.items()):
        print(f"  {brand}: {count}")
    
    print(f"\nSaving files...")
    
    # Save all lenses
    all_json = os.path.join(output_dir, 'all_lenses_complete.json')
    with open(all_json, 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print(f"  [SAVED] all_lenses_complete.json ({len(lenses)} lenses)")
    
    all_csv = os.path.join(output_dir, 'all_lenses_complete.csv')
    with open(all_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print(f"  [SAVED] all_lenses_complete.csv")
    
    # Save brand breakdown
    brand_json = os.path.join(output_dir, 'brand_breakdown.json')
    with open(brand_json, 'w', encoding='utf-8') as f:
        json.dump(brand_counts, f, indent=2)
    print(f"  [SAVED] brand_breakdown.json")
    
    # Save Sony brand lenses
    if sony_lenses:
        sony_json = os.path.join(output_dir, 'sony_brand_lenses.json')
        with open(sony_json, 'w', encoding='utf-8') as f:
            json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
        print(f"  [SAVED] sony_brand_lenses.json ({len(sony_lenses)} lenses)")
        
        sony_csv = os.path.join(output_dir, 'sony_brand_lenses.csv')
        with open(sony_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony_lenses[0].keys())
            writer.writeheader()
            writer.writerows(sony_lenses)
        print(f"  [SAVED] sony_brand_lenses.csv")
    
    # Save per-brand files
    for brand in BRANDS:
        brand_lenses = [l for l in lenses if brand in l.get('lens_name', '')]
        if brand_lenses:
            brand_file = os.path.join(output_dir, f'{brand.lower()}_lenses.json')
            with open(brand_file, 'w', encoding='utf-8') as f:
                json.dump(brand_lenses, f, indent=2, ensure_ascii=False)
            print(f"  [SAVED] {brand.lower()}_lenses.json ({len(brand_lenses)} lenses)")


def main():
    """Main"""
    try:
        lenses = scrape_all_data()
        
        if lenses:
            save_data(lenses)
            
            brand_counts = analyze_brands(lenses)
            
            print("\n" + "="*70)
            print("FINAL SUMMARY")
            print("="*70)
            print(f"Total Sony E-mount lenses: {len(lenses)}")
            print(f"\nBreakdown by brand:")
            for brand, count in sorted(brand_counts.items()):
                print(f"  {brand}: {count}")
            print(f"\nOutput files:")
            print("  - all_lenses_complete.json (all lenses)")
            print("  - all_lenses_complete.csv (all lenses)")
            print("  - brand_breakdown.json (counts per brand)")
            print("  - sony_brand_lenses.json (Sony brand only)")
            print("  - {brand}_lenses.json (individual brand files)")
            print("="*70)
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
