import requests

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

# Save full raw HTML
with open('raw_page.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)

print(f"Saved raw HTML ({len(resp.text)} chars)")

# Look for model details
print("\nSearching for model details...")

terms = ['Kingston', 'Furry', 'GAMING', 'PLUS', 'MAX', 'TOMAHAWK', 'HyperX', 'Hyperx']
for term in terms:
    if term in resp.text:
        print(f"  Found: {term}")
        idx = resp.text.find(term)
        # Look at surrounding context
        start = max(0, idx - 200)
        end = min(len(resp.text), idx + 200)
        context = resp.text[start:end]
        print(f"    Context: ...{context}...")
    else:
        print(f"  NOT FOUND: {term}")
