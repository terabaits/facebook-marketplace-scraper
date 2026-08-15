import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

# Search entire HTML for key terms
print("SEARCHING FULL HTML:")
print("="*60)

html_text = resp.text

# Find Kingston
if 'Kingston' in html_text:
    print("\n'Kingston' found:")
    idx = html_text.find('Kingston')
    print(f"Context: {html_text[max(0,idx-100):idx+150]}")

# Find Furry  
if 'Furry' in html_text:
    print("\n'Furry' found:")
    idx = html_text.find('Furry')
    print(f"Context: {html_text[max(0,idx-100):idx+150]}")

# Find GAMING
if 'GAMING' in html_text:
    print("\n'GAMING' found:")
    idx = html_text.find('GAMING')
    print(f"Context: {html_text[max(0,idx-100):idx+150]}")

# Find PLUS
if 'PLUS' in html_text:
    print("\n'PLUS' found:")
    idx = html_text.find('PLUS')
    print(f"Context: {html_text[max(0,idx-100):idx+150]}")

# Find MAX
if 'MAX' in html_text:
    print("\n'MAX' found:")
    idx = html_text.find('MAX')
    print(f"Context: {html_text[max(0,idx-100):idx+150]}")

# Check msg_div_msg content  
print("\n" + "="*60)
print("MSG_DIV_MSG CONTENT:")
print("="*60)
desc = soup.find('div', id='msg_div_msg')
if desc:
    print(desc.prettify()[:3000])
