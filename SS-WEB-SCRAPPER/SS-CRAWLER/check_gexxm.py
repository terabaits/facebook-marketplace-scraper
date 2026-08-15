"""Check gexxm.html listing content"""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}

resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
desc = soup.find('div', id='msg_div_msg')
description = desc.get_text(separator='\n') if desc else ""

print("LISTING TEXT:")
print("="*60)
print(f"Title: {title}")
print(f"\nDescription:")
print(description)
print("="*60)

# Check for RAM patterns
text_lower = (title + " " + description).lower()
print("\nRAM KEYWORDS FOUND:")
ram_keywords = ['ram', 'hyperx', 'fury', '32gb', '32 gb', 'ddr4', 'kingston']
for kw in ram_keywords:
    if kw in text_lower:
        idx = text_lower.find(kw)
        context = text_lower[max(0, idx-20):idx+len(kw)+20]
        print(f"  '{kw}' - ...{context}...")

# Check for motherboard patterns
print("\nMOTHERBOARD KEYWORDS FOUND:")
mb_keywords = ['msi', 'b450', 'tomahawk', 'max', 'mātesplate']
for kw in mb_keywords:
    if kw in text_lower:
        idx = text_lower.find(kw)
        context = text_lower[max(0, idx-20):idx+len(kw)+20]
        print(f"  '{kw}' - ...{context}...")
