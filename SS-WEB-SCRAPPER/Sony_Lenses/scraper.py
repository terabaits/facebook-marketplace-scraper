"""
Sony Lens Scraper for lab174.com - Working Implementation
Extracts all Sony lens data from the lab174.com database
"""

import json
import csv
import time
import re
from typing import List, Dict
from playwright.sync_api import sync_playwright


class SonyLensScraper:
    """Scraper for Sony lenses from lab174.com"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.lenses: List[Dict] = []
        self.all_lenses: List[Dict] = []
    
    def scrape(self) -> List[Dict]:
        """Main scrape method"""
        print("=" * 60)
        print("Starting Sony Lens Scraper")
        print("=" * 60)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            try:
                # Load page
                print(f"\nLoading {self.BASE_URL}...")
                page.goto(self.BASE_URL, wait_until='networkidle')
                time.sleep(2)
                
                all_data = []
                seen_names = set()
                page_num = 1
                
                while page_num <= 10:  # Max 10 pages
                    print(f"\n--- Processing page {page_num} ---")
                    
                    # Extract data from table
                    rows = page.query_selector_all('table tbody tr')
                    if not rows:
                        rows = page.query_selector_all('table tr')[1:]
                    
                    page_lenses = []
                    for row in rows:
                        try:
                            cells = row.query_selector_all('td')
                            if len(cells) >= 14:
                                lens = {
                                    'lens_name': cells[0].inner_text().strip(),
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
                                }
                                if lens['lens_name'] and lens['lens_name'] not in seen_names:
                                    seen_names.add(lens['lens_name'])
                                    page_lenses.append(lens)
                        except:
                            continue
                    
                    print(f"Found {len(page_lenses)} new lenses")
                    all_data.extend(page_lenses)
                    
                    # Try to click next
                    try:
                        next_btn = page.locator('button:has-text("Go to next page")')
                        if next_btn.count() == 0 or next_btn.is_disabled():
                            print("No more pages")
                            break
                        
                        next_btn.click()
                        time.sleep(2)
                        page_num += 1
                    except:
                        break
                
                # Filter Sony lenses
                self.all_lenses = all_data
                self.lenses = [l for l in all_data if self._is_sony(l['lens_name'])]
                
                print(f"\n{'='*60}")
                print(f"Total lenses: {len(self.all_lenses)}")
                print(f"Sony lenses: {len(self.lenses)}")
                print(f"{'='*60}")
                
                return self.lenses
                
            finally:
                browser.close()
    
    def _is_sony(self, name: str) -> bool:
        """Check if Sony lens"""
        n = name.lower()
        return any(k in n for k in ['sony', 'fe ', 'vario-tessar', 'za oss'])
    
    def save(self, base_path: str = "sony_lenses"):
        """Save data to files"""
        # Save all lenses JSON
        with open(f"{base_path}_all.json", 'w', encoding='utf-8') as f:
            json.dump(self.all_lenses, f, indent=2, ensure_ascii=False)
        
        # Save Sony lenses JSON
        with open(f"{base_path}.json", 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        
        # Save Sony lenses CSV
        if self.lenses:
            fields = ['lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
                     'year', 'min_focus_distance', 'max_magnification', 'weight',
                     'weight_class', 'length', 'aperture_ring', 'autofocus',
                     'category', 'macro', 'price']
            
            with open(f"{base_path}.csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(self.lenses)
        
        print(f"\nSaved {len(self.lenses)} Sony lenses to:")
        print(f"  - {base_path}.json")
        print(f"  - {base_path}.csv")


def main():
    scraper = SonyLensScraper()
    lenses = scraper.scrape()
    
    if lenses:
        scraper.save("sony_lenses")
        
        print("\n" + "="*60)
        print("Sample Sony Lenses:")
        print("="*60)
        for i, lens in enumerate(lenses[:5], 1):
            print(f"\n{i}. {lens['lens_name']}")
            print(f"   Focal: {lens['focal_length_wide']}-{lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Weight: {lens['weight']}")
            print(f"   Price: {lens['price']}")
    else:
        print("No Sony lenses found!")


if __name__ == "__main__":
    main()
