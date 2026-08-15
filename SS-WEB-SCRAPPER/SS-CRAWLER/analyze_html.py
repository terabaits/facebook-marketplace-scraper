"""Analyze the HTML structure of the listing"""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')
desc = soup.find('div', id='msg_div_msg')

print("FULL HTML STRUCTURE:")
print("="*60)
print(desc.prettify()[:4000])
print("\n\n" + "="*60)
print("OPTIONS LIST TABLE ROWS:")
print("="*60)

# Find options_list table
table = desc.find('table', class_='options_list')
if table:
    rows = table.find_all('tr')
    for i, row in enumerate(rows):
        tds = row.find_all('td')
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True)
            value = tds[1].get_text(strip=True)
            print(f"Row {i}: '{label}' -> '{value}'")
            
            # Check inner HTML of value cell
            if 'Kingston' in str(tds[1]) or 'GAMING' in str(tds[1]):
                print(f"  Inner HTML: {tds[1].prettify()}")
else:
    print("No options_list table found!")

# Also check for other tables
print("\n\n" + "="*60)
print("ALL TABLES IN DESC:")
print("="*60)
tables = desc.find_all('table')
for i, table in enumerate(tables):
    print(f"\nTable {i} (class={table.get('class')}):")
    rows = table.find_all('tr')
    for row in rows[:5]:  # First 5 rows
        tds = row.find_all('td')
        if len(tds) >= 2:
            print(f"  '{tds[0].get_text(strip=True)}' -> '{tds[1].get_text(strip=True)}'")
