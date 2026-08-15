import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

desc = soup.find('div', id='msg_div_msg')
text = desc.get_text(separator='\n') if desc else ""

print("RAW TEXT:")
print(repr(text))
print("\n\nFORMATTED:")
print(text)

# Check for specific patterns
t_lower = text.lower()
print("\n\nPATTERN CHECKS:")
print(f"'gaming plus' in text: {'gaming plus' in t_lower}")
print(f"'tomahawk' in text: {'tomahawk' in t_lower}")
print(f"'b450' in text: {'b450' in t_lower}")

# Find lines with motherboard info
for i, line in enumerate(text.split('\n')):
    if 'plate' in line.lower() or 'msi' in line.lower() or 'b450' in line.lower():
        print(f"\nLine {i}: {line}")
