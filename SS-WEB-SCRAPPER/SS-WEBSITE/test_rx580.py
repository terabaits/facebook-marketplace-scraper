import requests

# Test RX580 detection
test_cases = [
    "RX 580 8GB Graphics Card",
    "AMD Radeon RX580 8GB",
    "Sapphire RX 580 Nitro+ 8GB",
    "RX580 4GB GPU",
    "Radeon RX 580 Gaming",
]

for title in test_cases:
    print(f"\nTesting: '{title}'")
    try:
        response = requests.post('http://localhost:5001/api/v1/extension/analyze', 
            json={
                'title': title,
                'description': 'Good condition, works perfectly',
                'price': 150,
                'currency': 'EUR'
            })
        data = response.json()
        if data.get('success') and data.get('components'):
            print(f"  Detected: {data['components']}")
        else:
            print(f"  No components detected: {data.get('error', 'unknown')}")
    except Exception as e:
        print(f"  Error: {e}")
