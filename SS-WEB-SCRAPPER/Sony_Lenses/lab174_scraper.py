"""
Sony Lens Scraper for lab174.com
Scrapes Sony E-mount lens data from the lab174.com lenses database
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
from pathlib import Path
from typing import List, Dict, Optional


class Lab174Scraper:
    """Scraper for lab174.com lens database"""
    
    BASE_URL = "https://lab174.com/lenses/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.lenses: List[Dict] = []
        
    def fetch_page(self, page_num: int = 1) -> Optional[BeautifulSoup]:
        """Fetch a specific page of lens data"""
        try:
            # The page uses client-side pagination, so we need to get all data
            # First, let's check if there's an API or if data is embedded
            url = self.BASE_URL
            if page_num > 1:
                # Try to find pagination parameter
                url = f"{self.BASE_URL}?page={page_num}"
            
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching page {page_num}: {e}")
            return None
    
    def parse_lens_row(self, row) -> Optional[Dict]:
        """Parse a single lens row from the table"""
        try:
            # Get all cells in the row
            cells = row.find_all(['td', 'th'])
            if len(cells) < 14:  # Minimum expected columns
                return None
            
            # Extract data from cells
            lens_data = {
                'lens_name': self._clean_text(cells[0].get_text()),
                'focal_length_wide': self._clean_text(cells[1].get_text()),
                'focal_length_tele': self._clean_text(cells[2].get_text()),
                'f_stop': self._clean_text(cells[3].get_text()),
                'year': self._clean_text(cells[4].get_text()),
                'min_focus_distance': self._clean_text(cells[5].get_text()),
                'max_magnification': self._clean_text(cells[6].get_text()),
                'weight': self._clean_text(cells[7].get_text()),
                'weight_class': self._clean_text(cells[8].get_text()),
                'length': self._clean_text(cells[9].get_text()),
                'aperture_ring': self._clean_text(cells[10].get_text()),
                'autofocus': self._clean_text(cells[11].get_text()),
                'category': self._clean_text(cells[12].get_text()),
                'macro': self._clean_text(cells[13].get_text()),
                'price': self._clean_text(cells[14].get_text()) if len(cells) > 14 else None,
            }
            
            # Only include Sony lenses
            if 'sony' in lens_data['lens_name'].lower() or 'fe' in lens_data['lens_name'].lower():
                return lens_data
            
            # Also check for Zeiss Sony lenses
            if 'vario-tessar' in lens_data['lens_name'].lower() or 'za' in lens_data['lens_name'].lower():
                return lens_data
                
            return None
            
        except Exception as e:
            print(f"Error parsing row: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace"""
        if text is None:
            return ""
        return ' '.join(text.strip().split())
    
    def scrape_all_lenses(self) -> List[Dict]:
        """Scrape all lens data from the website"""
        soup = self.fetch_page(1)
        if not soup:
            print("Failed to fetch initial page")
            return []
        
        # Find the table with lens data
        table = soup.find('table')
        if not table:
            print("Could not find lens table")
            return []
        
        # Find all rows (skip header row)
        rows = table.find_all('tr')[1:]  # Skip header
        
        print(f"Found {len(rows)} total rows in table")
        
        sony_lenses = []
        for row in rows:
            lens_data = self.parse_lens_row(row)
            if lens_data:
                sony_lenses.append(lens_data)
        
        print(f"Found {len(sony_lenses)} Sony lenses")
        self.lenses = sony_lenses
        return sony_lenses
    
    def save_to_json(self, filepath: str):
        """Save lens data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.lenses, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.lenses)} lenses to {filepath}")
    
    def save_to_csv(self, filepath: str):
        """Save lens data to CSV file"""
        if not self.lenses:
            print("No data to save")
            return
        
        fieldnames = [
            'lens_name', 'focal_length_wide', 'focal_length_tele', 'f_stop',
            'year', 'min_focus_distance', 'max_magnification', 'weight',
            'weight_class', 'length', 'aperture_ring', 'autofocus',
            'category', 'macro', 'price'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.lenses)
        print(f"Saved {len(self.lenses)} lenses to {filepath}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("Sony Lens Scraper for lab174.com")
    print("=" * 60)
    
    scraper = Lab174Scraper()
    lenses = scraper.scrape_all_lenses()
    
    if lenses:
        # Save to both JSON and CSV
        scraper.save_to_json('sony_lenses.json')
        scraper.save_to_csv('sony_lenses.csv')
        
        print("\n" + "=" * 60)
        print(f"Scraping complete! Found {len(lenses)} Sony lenses")
        print("=" * 60)
        
        # Print first few lenses as sample
        print("\nSample data:")
        for i, lens in enumerate(lenses[:3]):
            print(f"\n{i+1}. {lens['lens_name']}")
            print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Price: {lens['price']}")
    else:
        print("No lenses found!")


if __name__ == "__main__":
    main()
