import requests

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'

# Save raw HTML
with open('G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/debug_gexxm.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)

print("Saved to debug_gexxm.html")
print(f"Response length: {len(resp.text)} chars")

# Look for the specific content
if 'Kingston' in resp.text:
    print("\n'Kingston' found in raw HTML")
    idx = resp.text.find('Kingston')
    print(f"Context: {resp.text[max(0,idx-50):idx+100]}")
    
if 'GAMING' in resp.text:
    print("\n'GAMING' found in raw HTML")
    idx = resp.text.find('GAMING')
    print(f"Context: {resp.text[max(0,idx-50):idx+100]}")
