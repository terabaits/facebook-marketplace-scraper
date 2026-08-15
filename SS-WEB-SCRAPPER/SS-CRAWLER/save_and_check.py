import requests

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

# Save full HTML
with open('gexxm_full.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)

print("Saved to gexxm_full.html")

# Check for Kingston and GAMING in raw HTML
print("\nRaw HTML search:")
print(f"'Kingston' in HTML: {'Kingston' in resp.text}")
print(f"'Furry' in HTML: {'Furry' in resp.text}")
print(f"'GAMING' in HTML: {'GAMING' in resp.text}")
print(f"'PLUS' in HTML: {'PLUS' in resp.text}")
print(f"'MAX' in HTML: {'MAX' in resp.text}")
print(f"'TOMAHAWK' in HTML: {'TOMAHAWK' in resp.text}")

# Find contexts
for kw in ['Kingston', 'Furry', 'GAMING', 'TOMAHAWK']:
    if kw in resp.text:
        idx = resp.text.find(kw)
        print(f"\n{kw} context:")
        print(resp.text[max(0,idx-100):idx+100])
