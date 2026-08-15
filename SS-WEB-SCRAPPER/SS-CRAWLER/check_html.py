import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

print("RAW HTML around msg_div_msg:")
print("="*60)

soup = BeautifulSoup(resp.text, 'html.parser')
desc = soup.find('div', id='msg_div_msg')

if desc:
    print("Found msg_div_msg:")
    print(desc.prettify()[:3000])
else:
    print("msg_div_msg not found!")
    
# Also check the table structure
print("\n\n" + "="*60)
print("CHECKING TABLE STRUCTURE:")
print("="*60)

tables = soup.find_all('table')
for i, table in enumerate(tables):
    print(f"\nTable {i}:")
    print(table.get_text(separator='\n')[:500])
