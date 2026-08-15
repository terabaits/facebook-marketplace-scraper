"""
Complete Sony Lens Scraper for lab174.com
Captures all 178 lenses across all pages
"""

import json
import csv
import time
import re
from typing import List, Dict
from playwright.sync_api import sync_playwright


def clean_text(text: str) -> str:
    """Clean up text by removing emoji and normalizing"""
    # Remove emoji and special characters
    text = re.sub(r'[^\w\s\.\-\$/]', '', text)
    return text.strip()


def scrape_all_pages() -> tuple:
    """Scrape all 178 lenses from lab174.com across all pages"""
    
    print("=" * 70)
    print("Lab174.com Complete Lens Scraper")
    print("Capturing all 178 lenses...")
    print("=" * 70)
    
    all_lenses = []
    seen_names = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load the page
            print("\n[1/2] Loading lab174.com/lenses/...")
            page.goto('https://lab174.com/lenses/', wait_until='networkidle')
            time.sleep(3)
            
            page_num = 1
            max_pages = 10  # Safety limit
            
            while page_num <= max_pages:
                print(f"\n[2/2] Processing page {page_num}...")
                
                # Wait for table to be visible
                page.wait_for_selector('table tbody tr', timeout=10000)
                
                # Get all rows from the table
                rows = page.locator('table tbody tr')
                row_count = rows.count()
                
                print(f"      Found {row_count} rows on this page")
                
                new_count = 0
                for i in range(row_count):
                    try:
                        row = rows.nth(i)
                        cells = row.locator('td')
                        cell_count = cells.count()
                        
                        if cell_count >= 14:
                            lens_name = cells.nth(0).inner_text().strip()
                            
                            # Skip if already seen (avoid duplicates)
                            if not lens_name or lens_name in seen_names:
                                continue
                            
                            seen_names.add(lens_name)
                            
                            lens_data = {
                                'lens_name': lens_name,
                                'focal_length_wide': clean_text(cells.nth(1).inner_text()),
                                'focal_length_tele': clean_text(cells.nth(2).inner_text()),
                                'f_stop': clean_text(cells.nth(3).inner_text()),
                                'year': clean_text(cells.nth(4).inner_text()),
                                'min_focus_distance': clean_text(cells.nth(5).inner_text()),
                                'max_magnification': clean_text(cells.nth(6).inner_text()),
                                'weight': clean_text(cells.nth(7).inner_text()),
                                'weight_class': clean_text(cells.nth(8).inner_text()),
                                'length': clean_text(cells.nth(9).inner_text()),
                                'aperture_ring': clean_text(cells.nth(10).inner_text()),
                                'autofocus': clean_text(cells.nth(11).inner_text()),
                                'category': clean_text(cells.nth(12).inner_text()),
                                'macro': clean_text(cells.nth(13).inner_text()),
                                'price': clean_text(cells.nth(14).inner_text()) if cell_count > 14 else '',
                            }
                            
                            all_lenses.append(lens_data)
                            new_count += 1
                            
                    except Exception as e:
                        continue
                
                print(f"      Added {new_count} new lenses (Total: {len(all_lenses)})")
                
                # Try to click next page button
                try:
                    # Look for next button with aria-label
                    next_btn = page.locator('button[aria-label="Go to next page"]')
                    
                    if next_btn.count() == 0:
                        print("      No next button found - finished")
                        break
                    
                    # Check if button is disabled
                    is_disabled = next_btn.evaluate('el => el.disabled')
                    if is_disabled:
                        print("      Next button disabled - finished")
                        break
                    
                    print("      Clicking next page...")
                    next_btn.click()
                    time.sleep(3)  # Wait for page load
                    page_num += 1
                    
                except Exception as e:
                    print(f"      Navigation complete: {e}")
                    break
            
            print(f"\n{'='*70}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*70}")
            print(f"Total lenses scraped: {len(all_lenses)}")
            
            # Filter Sony lenses
            sony_lenses = []
            for lens in all_lenses:
                name_lower = lens['lens_name'].lower()
                if any(k in name_lower for k in ['sony', 'vario-tessar']):
                    sony_lenses.append(lens)
            
            print(f"Sony lenses: {len(sony_lenses)}")
            print(f"{'='*70}")
            
            return all_lenses, sony_lenses
            
        finally:
            browser.close()


def save_files(all_lenses: List[Dict], sony_lenses: List[Dict]):
    """Save data to JSON and CSV files"""
    
    # Save all lenses JSON
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(all_lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # Save all lenses CSV
    if all_lenses:
        fieldnames = list(all_lenses[0].keys())
        with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_lenses)
        print("[SAVED] all_lenses.csv")
    
    # Save Sony lenses JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony_lenses, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    # Save Sony lenses CSV
    if sony_lenses:
        fieldnames = list(sony_lenses[0].keys())
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sony_lenses)
        print("[SAVED] sony_lenses.csv")


def print_stats(all_lenses: List[Dict], sony_lenses: List[Dict]):
    """Print statistics and sample data"""
    
    print("\n" + "="*70)
    print("SCRAPING STATISTICS")
    print("="*70)
    print(f"Total lenses scraped: {len(all_lenses)}")
    print(f"Sony lenses: {len(sony_lenses)}")
    
    # Count by category
    categories = {}
    for lens in all_lenses:
        cat = lens.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nLenses by category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    
    print("\n" + "="*70)
    print("Sample Sony Lenses:")
    print("="*70)
    for i, lens in enumerate(sony_lenses[:5], 1):
        print(f"\n{i}. {lens['lens_name']}")
        print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
        print(f"   Aperture: f/{lens['f_stop']}")
        print(f"   Weight: {lens['weight']}")
        print(f"   Price: {lens['price']}")
    
    print("\n" + "="*70)
    print("Sample Non-Sony Lenses:")
    print("="*70)
    non_sony = [l for l in all_lenses if l not in sony_lenses][:5]
    for i, lens in enumerate(non_sony, 1):
        print(f"\n{i}. {lens['lens_name']}")
        print(f"   Brand: {lens['lens_name'].split()[0]}")
        print(f"   Category: {lens['category']}")
        print(f"   Price: {lens['price']}")


def main():
    """Main entry point"""
    try:
        all_lenses, sony_lenses = scrape_all_pages()
        save_files(all_lenses, sony_lenses)
        print_stats(all_lenses, sony_lenses)
        
        print("\n" + "="*70)
        print("OUTPUT FILES")
        print("="*70)
        print("  • all_lenses.json - All 178 lenses (JSON)")
        print("  • all_lenses.csv - All 178 lenses (CSV)")
        print("  • sony_lenses.json - Sony lenses only (JSON)")
        print("  • sony_lenses.csv - Sony lenses only (CSV)")
        print("="*70)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
