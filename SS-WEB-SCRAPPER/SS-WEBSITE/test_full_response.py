import requests
import sys

response = requests.get('http://localhost:5000/api/stats')

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"\nResponse text (first 2000 chars):")
print(response.text[:2000])

# Try to parse
try:
    data = response.json()
    print(f"\n\nParsed JSON keys: {list(data.keys())}")
    if 'ram' in data:
        print(f"RAM data: {data['ram']}")
    else:
        print("RAM key NOT in response!")
except Exception as e:
    print(f"\n\nJSON parse error: {e}")
    print(f"Raw response: {response.text[:500]}")
