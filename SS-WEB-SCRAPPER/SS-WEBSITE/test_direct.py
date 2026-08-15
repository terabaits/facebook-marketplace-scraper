import requests
import json

# Test with direct debug
test_data = {
    "title": "Palit GameRock 1080TI 11gb",
    "description": "",
    "price": 130,
    "currency": "EUR",
    "listing_url": "https://facebook.com/test_direct",
    "image_url": "",
    "seller_location": "Test"
}

print("=== Direct test ===")
r = requests.post(
    'http://localhost:5001/api/v1/extension/analyze',
    json=test_data,
    headers={'Content-Type': 'application/json'}
)

print(f"Status: {r.status_code}")
data = r.json()

if data.get('success'):
    print(f"Full response: {json.dumps(data, indent=2)}")
    
    # Check where matched_id is
    components = data.get('components', {})
    if 'gpu' in components:
        gpu = components['gpu']
        print(f"\nGPU structure: {json.dumps(gpu, indent=2)}")
        
        # Check both possible locations
        if 'matched_model' in gpu:
            print(f"\nmatched_model.id: {gpu['matched_model'].get('id')}")
        print(f"gpu.matched_id: {gpu.get('matched_id')}")
