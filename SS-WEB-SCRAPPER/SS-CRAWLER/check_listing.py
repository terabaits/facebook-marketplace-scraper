import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

desc = soup.find('div', id='msg_div_msg')
text = desc.get_text(separator='\n') if desc else ""

print("FULL LISTING TEXT:")
print("="*60)
print(text)
print("="*60)

t_lower = text.lower()

print("\n\nSPECIFIC CHECKS:")
print(f"'furry' in text: {'furry' in t_lower}")
print(f"'fury' in text: {'fury' in t_lower}")
print(f"'hyperx' in text: {'hyperx' in t_lower}")
print(f"'gaming plus' in text: {'gaming plus' in t_lower}")
print(f"'gaming' in text: {'gaming' in t_lower}")
print(f"'plus' in text: {'plus' in t_lower}")
print(f"'max' in text: {'max' in t_lower}")
print(f"'tomahawk' in text: {'tomahawk' in t_lower}")
print(f"'b450' in text: {'b450' in t_lower}")

# Find lines with RAM
print("\n\nLINES WITH RAM INFO:")
for i, line in enumerate(text.split('\n')):
    l = line.lower()
    if any(kw in l for kw in ['ram', 'operativ', 'atmiņ', 'hyperx', 'furry', 'fury']):
        print(f"Line {i}: {line}")

# Find lines with MB
print("\n\nLINES WITH MOTHERBOARD INFO:")
for i, line in enumerate(text.split('\n')):
    l = line.lower()
    if any(kw in l for kw in ['plate', 'msi', 'b450', 'gaming', 'tomahawk']):
        print(f"Line {i}: {line}")
