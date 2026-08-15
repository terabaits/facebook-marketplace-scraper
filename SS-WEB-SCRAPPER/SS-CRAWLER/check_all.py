import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

# Get all text from the page
all_text = soup.get_text(separator='\n')

print("ALL TEXT FROM PAGE:")
print("="*60)
print(all_text)
print("="*60)

# Check for specific terms
t_lower = all_text.lower()
print("\nCHECKS:")
print(f"'kingston' in text: {'kingston' in t_lower}")
print(f"'furry' in text: {'furry' in t_lower}")
print(f"'fury' in text: {'fury' in t_lower}")
print(f"'hyperx' in text: {'hyperx' in t_lower}")
print(f"'gaming' in text: {'gaming' in t_lower}")
print(f"'plus' in text: {'plus' in t_lower}")
print(f"'max' in text: {'max' in t_lower}")
print(f"'tomahawk' in text: {'tomahawk' in t_lower}")
