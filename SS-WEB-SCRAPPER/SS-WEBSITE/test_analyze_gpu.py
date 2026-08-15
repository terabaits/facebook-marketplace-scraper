import requests
import json

# Test the analyze endpoint with a GPU listing
test_data = {
    "title": "Palit GameRock 1080TI 11gb",
    "description": "",
    "price": 130,
    "currency": "EUR",
    "listing_url": "https://facebook.com/marketplace/test123",
    "image_url": "",
    "seller_location": "Test Location"
}

print("=== Testing Extension API /analyze ===")
try:
    r = requests.post(
        'http://localhost:5001/api/v1/extension/analyze',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    
    if data.get('success'):
        components = data.get('components', {})
        print(f"\nDetected components: {list(components.keys())}")
        
        if 'gpu' in components:
            gpu = components['gpu']
            print(f"\nGPU Detection:")
            print(f"  detected: {gpu.get('detected')}")
            print(f"  normalized: {gpu.get('normalized')}")
            print(f"  matched_id: {gpu.get('matched_id')}")
            print(f"  confidence: {gpu.get('confidence')}")
            
            if gpu.get('matched_id'):
                print("\n*** matched_id EXISTS - import should work! ***")
            else:
                print("\n*** matched_id is NULL - this is the problem! ***")
        else:
            print("\n*** No GPU detected in title! ***")
    else:
        print(f"Error: {data.get('error')}")
        
except Exception as e:
    print(f"Error: {e}")
