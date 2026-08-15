import requests
import json

# Test various GPU titles
test_cases = [
    {"title": "Palit GameRock 1080TI 11gb", "expected": "1080 Ti"},
    {"title": "GTX 1080 /8 GB/ Founders Edition", "expected": "GTX 1080"},
    {"title": "RTX 3070 Ti", "expected": "RTX 3070 Ti"},
    {"title": "RX 580 8GB", "expected": "RX 580"},
    {"title": "Nvidia RTX 4090", "expected": "RTX 4090"},
]

print("=== Testing Extension GPU Detection ===\n")

for case in test_cases:
    test_data = {
        "title": case["title"],
        "description": "",
        "price": 100,
        "currency": "EUR",
        "listing_url": "https://facebook.com/test",
        "image_url": "",
        "seller_location": "Test"
    }
    
    try:
        r = requests.post(
            'http://localhost:5001/api/v1/extension/analyze',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        data = r.json()
        
        if data.get('success') and 'gpu' in data.get('components', {}):
            gpu = data['components']['gpu']
            matched_id = gpu.get('matched_id')
            status = "✅" if matched_id else "❌ NO ID"
            print(f"{status} '{case['title'][:40]}...'")
            print(f"    Detected: {gpu.get('detected')}")
            print(f"    Normalized: {gpu.get('normalized')}")
            print(f"    Matched ID: {matched_id}")
        else:
            print(f"❌ '{case['title'][:40]}...' - No GPU detected")
            
    except Exception as e:
        print(f"❌ '{case['title'][:40]}...' - Error: {e}")
    
    print()
