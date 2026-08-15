import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

soup = BeautifulSoup(resp.text, 'html.parser')

# Check if the detailed specs exist
print("ALL TEXT FROM PAGE:")
print("="*60)
all_text = soup.get_text(separator='\n')
print(all_text)
print("="*60)

# Look for specific terms
print("\nSearching for model details...")
terms = ['kingston', 'furry', 'gaming', 'plus', 'max', 'tomahawk']
for term in terms:
    if term in all_text.lower():
        print(f"  Found: {term}")
        # Find context
        idx = all_text.lower().find(term)
        context = all_text[max(0, idx-50):idx+50]
        print(f"    Context: {context}")
    else:
        print(f"  NOT FOUND: {term}")
