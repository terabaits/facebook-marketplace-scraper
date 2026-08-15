"""Explore the lab174.com page structure to find all lens data"""

import requests
import re
from bs4 import BeautifulSoup

url = 'https://lab174.com/lenses/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Fetching page...")
response = requests.get(url, headers=headers)
html = response.text

# Look for data in script tags
print("\nSearching for lens data in scripts...")
lenses_data = re.search(r'(lenses|data)\s*=\s*(\[.*?\])', html, re.DOTALL | re.IGNORECASE)
if lenses_data:
    print('Found lens data in HTML')
    print(lenses_data.group()[:1000])

# Check if there's a JSON data file
print('\nLooking for JSON data files...')
json_matches = re.findall(r'[^\'"\s]+\.json', html)
print(f'JSON files found: {json_matches}')

# Look for data in window object
print('\nSearching for window data...')
window_data = re.search(r'window\.__\w+__\s*=\s*({.*?})', html, re.DOTALL)
if window_data:
    print('Found window data')
    print(window_data.group()[:500])

# Parse with BeautifulSoup and check for table
print('\n\nParsing HTML...')
soup = BeautifulSoup(html, 'html.parser')
table = soup.find('table')

if table:
    rows = table.find_all('tr')
    print(f'Total rows in table: {len(rows)}')
    
    # Get actual row count including data rows
    data_rows = table.find_all('tr', class_=False)  # Try to get data rows
    print(f'Data rows: {len(data_rows)}')
    
    # Try finding checkbox rows
    checkbox_rows = table.find_all('tr', {'role': 'row'})
    print(f'Checkbox/role rows: {len(checkbox_rows)}')

# Check for embedded data
print('\n\nChecking for embedded data structures...')
if 'const' in html or 'let' in html or 'var' in html:
    print('JavaScript variables found in page')
    
# Look for lens entries
lens_names = re.findall(r'(Sony FE [^<]+)', html)
print(f'\nFound {len(lens_names)} Sony FE mentions')
for name in lens_names[:10]:
    print(f'  - {name}')
