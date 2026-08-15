"""Find where the detailed specs are"""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

# Print the entire HTML structure around msg_div_msg
print("HTML STRUCTURE:")
print("="*60)

desc = soup.find('div', id='msg_div_msg')
if desc:
    # Print all children
    for i, child in enumerate(desc.children):
        if hasattr(child, 'name') and child.name:
            print(f"\nChild {i}: <{child.name}>")
            if child.name == 'table':
                # Print table rows
                for row in child.find_all('tr'):
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        print(f"  Row: '{tds[0].get_text(strip=True)}' -> '{tds[1].get_text(strip=True)}'")
                        # Check innerHTML of second cell
                        val_html = str(tds[1])
                        if 'Kingston' in val_html or 'Furry' in val_html or 'GAMING' in val_html:
                            print(f"    HTML: {val_html}")
            else:
                text = child.get_text(strip=True)
                if text:
                    print(f"  Text: {text[:100]}")

# Also check for any b or strong tags
print("\n" + "="*60)
print("BOLD/STRONG TEXT:")
print("="*60)
for elem in soup.find_all(['b', 'strong']):
    text = elem.get_text(strip=True)
    if text and len(text) > 3:
        print(f"  {text}")

# Check for any spans with style
print("\n" + "="*60)
print("SPANS:")
print("="*60)
for elem in soup.find_all('span'):
    text = elem.get_text(strip=True)
    if text and len(text) > 3 and any(x in text.lower() for x in ['kingston', 'msi', 'b450']):
        print(f"  {text}")
