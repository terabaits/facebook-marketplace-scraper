"""
Sony Lens Scraper for lab174.com using Selenium
Handles dynamic pagination and JavaScript-rendered content
"""

import json
import csv
import time
import re
from pathlib import Path
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup


class Lab174SeleniumScraper:
    """Scraper for lab174.com using Selenium for JavaScript-rendered content"""
    
    BASE_URL = "https://lab174.com/lenses/"
    
    def __init__(self):
        self.driver = None
        self.lenses: List[Dict] = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print("Make sure Chrome and ChromeDriver are installed")
            raise
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
    
    def extract_data_from_page(self) -> List[Dict]:
        """Extract lens data from current page"""
        page_lenses = []
        
        # Find the table
        try:
            table = self.driver.find_element(By.TAG_NAME, 'table')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            
            # Skip header row
            for row in rows[1:]:
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 14:
                        lens_data = {
                            'lens_name': cells[0].text.strip(),
                            'focal_length_wide': cells[1].text.strip(),
                            'focal_length_tele': cells[2].text.strip(),
                            'f_stop': cells[3].text.strip(),
                            'year': cells[4].text.strip(),
                            'min_focus_distance': cells[5].text.strip(),
                            'max_magnification': cells[6].text.strip(),
                            'weight': cells[7].text.strip(),
                            'weight_class': cells[8].text.strip(),
                            'length': cells[9].text.strip(),
                            'aperture_ring': cells[10].text.strip(),
                            'autofocus': cells[11].text.strip(),
                            'category': cells[12].text.strip(),
                            'macro': cells[13].text.strip(),
                            'price': cells[14].text.strip() if len(cells) > 14 else '',
                        }
                        page_lenses.append(lens_data)
                except Exception as e:
                    continue
        except Exception as e:
            print(f"Error extracting data: {e}")
        
        return page_lenses
    
    def is_sony_lens(self, lens_name: str) -> bool:
        """Check if lens is a Sony lens"""
        name_lower = lens_name.lower()
        # Include Sony branded lenses and Zeiss lenses made for Sony
        sony_indicators = ['sony', 'fe ', 'e ', 'vario-tessar', 'za ', 'g ', 'gm']
        return any(indicator in name_lower for indicator in sony_indicators)
    
    def scrape_all_lenses(self) -> List[Dict]:
        """Scrape all lens data across all pages"""
        self.setup_driver()
        
        try:
            print(f"Loading {self.BASE_URL}...")
            self.driver.get(self.BASE_URL)
            
            # Wait for the table to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'table')))
            
            # Wait a bit for JavaScript to fully render
            time.sleep(2)
            
            all_lenses = []
            page_num = 1
            
            while True:
                print(f"Processing page {page_num}...")
                
                # Extract data from current page
                page_lenses = self.extract_data_from_page()
                print(f"  Found {len(page_lenses)} lenses on this page")
                
                if not page_lenses:
                    break
                
                all_lenses.extend(page_lenses)
                
                # Try to click next page button
                try:
                    next_button = self.driver.find_element(
                        By.XPATH, 
                        "//button[contains(text(), 'next page') or contains(@aria-label, 'next page')]"
                    )
                    
                    # Check if button is disabled
                    if next_button.get_attribute('disabled'):
                        print("Next button is disabled - reached last page")
                        break
                    
                    # Click next page
                    next_button.click()
                    time.sleep(2)  # Wait for page to load
                    page_num += 1
                    
                except Exception as e:
                    print(f"Could not find or click next button: {e}")
                    break
            
            # Filter for Sony lenses only
            sony_lenses = [lens for lens in all_lenses if self.is_sony_lens(lens['lens_name'])]
            
            print(f"\nTotal lenses found: {len(all_lenses)}")
            print(f"Sony lenses found: {len(sony_lenses)}")
            
            self.lenses = sony_lenses
            return sony_lenses
            
        finally:
            self.close_driver()
    
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
    print("Sony Lens Scraper for lab174.com (Selenium)")
    print("=" * 60)
    
    scraper = Lab174SeleniumScraper()
    lenses = scraper.scrape_all_lenses()
    
    if lenses:
        # Save to both JSON and CSV
        scraper.save_to_json('sony_lenses_full.json')
        scraper.save_to_csv('sony_lenses_full.csv')
        
        print("\n" + "=" * 60)
        print(f"Scraping complete! Found {len(lenses)} Sony lenses")
        print("=" * 60)
        
        # Print first few lenses as sample
        print("\nSample data:")
        for i, lens in enumerate(lenses[:5]):
            print(f"\n{i+1}. {lens['lens_name']}")
            print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
            print(f"   Aperture: f/{lens['f_stop']}")
            print(f"   Price: {lens['price']}")
    else:
        print("No lenses found!")


if __name__ == "__main__":
    main()
