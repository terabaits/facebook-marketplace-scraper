"""
Direct HTML scrape of lab174.com
Parses the full page HTML to extract all lenses
"""

import requests
from bs4 import BeautifulSoup
import json
import csv


def scrape_with_requests():
    """Scrape using requests and BeautifulSoup"""
    
    print("="*70)
    print("Direct HTML Scrape of lab174.com")
    print("="*70)
    
    url = 'https://lab174.com/lenses/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("\nFetching page...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    print("Parsing HTML...")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table
    table = soup.find('table')
    if not table:
        print("No table found!")
        return []
    
    # Get all rows
    rows = table.find_all('tr')[1:]  # Skip header
    print(f"Found {len(rows)} rows in HTML")
    
    lenses = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 14:
            lens_data = {
                'lens_name': cells[0].get_text(strip=True),
                'focal_length_wide': cells[1].get_text(strip=True),
                'focal_length_tele': cells[2].get_text(strip=True),
                'f_stop': cells[3].get_text(strip=True),
                'year': cells[4].get_text(strip=True),
                'min_focus_distance': cells[5].get_text(strip=True),
                'max_magnification': cells[6].get_text(strip=True),
                'weight': cells[7].get_text(strip=True),
                'weight_class': cells[8].get_text(strip=True),
                'length': cells[9].get_text(strip=True),
                'aperture_ring': cells[10].get_text(strip=True),
                'autofocus': cells[11].get_text(strip=True),
                'category': cells[12].get_text(strip=True),
                'macro': cells[13].get_text(strip=True),
                'price': cells[14].get_text(strip=True) if len(cells) > 14 else '',
            }
            lenses.append(lens_data)
    
    print(f"Extracted {len(lenses)} lenses from HTML")
    return lenses


def save_files(lenses):
    """Save to files"""
    
    if not lenses:
        print("No lenses to save")
        return
    
    # Filter Sony lenses
    sony = [l for l in lenses if any(x in l['lens_name'].lower() for x in ['sony', 'vario-tessar'])]
    
    print(f"\nSony lenses: {len(sony)}")
    
    # Save all JSON
    with open('all_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print("\n[SAVED] all_lenses.json")
    
    # Save all CSV
    with open('all_lenses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lenses[0].keys())
        writer.writeheader()
        writer.writerows(lenses)
    print("[SAVED] all_lenses.csv")
    
    # Save Sony JSON
    with open('sony_lenses.json', 'w', encoding='utf-8') as f:
        json.dump(sony, f, indent=2, ensure_ascii=False)
    print("[SAVED] sony_lenses.json")
    
    # Save Sony CSV
    if sony:
        with open('sony_lenses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sony[0].keys())
            writer.writeheader()
            writer.writerows(sony)
        print("[SAVED] sony_lenses.csv")


def main():
    """Main"""
    try:
        lenses = scrape_with_requests()
        
        if lenses:
            save_files(lenses)
            
            print(f"\n{'='*70}")
            print(f"SUMMARY")
            print(f"{'='*70}")
            print(f"Total lenses: {len(lenses)}")
            print(f"Sony lenses: {len([l for l in lenses if 'sony' in l['lens_name'].lower() or 'vario-tessar' in l['lens_name'].lower()])}")
            print(f"\nFiles:")
            print("  - all_lenses.json")
            print("  - all_lenses.csv")
            print("  - sony_lenses.json")
            print("  - sony_lenses.csv")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
