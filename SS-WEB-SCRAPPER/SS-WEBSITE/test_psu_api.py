import requests

print("=== Testing /psus page ===")
try:
    r = requests.get('http://localhost:5000/psus')
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("HTML loaded OK")
    else:
        print(f"Error: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing /api/psus endpoint ===")
try:
    r = requests.get('http://localhost:5000/api/psus?active=true&min_confidence=0')
    print(f"Status: {r.status_code}")
    data = r.json()
    if isinstance(data, list):
        print(f"Listings count: {len(data)}")
        if len(data) > 0:
            print(f"First listing: {data[0].get('title', 'N/A')}")
    elif isinstance(data, dict) and 'error' in data:
        print(f"API Error: {data['error']}")
    else:
        print(f"Unexpected response: {data}")
except Exception as e:
    print(f"Error: {e}")
