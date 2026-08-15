import requests

print("=== Testing GPU Listing Popup ===")

# Get a GPU listing first
try:
    r = requests.get('http://localhost:5000/api/gpus?active=true&limit=1')
    data = r.json()
    
    if data and len(data) > 0:
        listing_id = data[0]['listing_id']
        print(f"Testing with listing ID: {listing_id}")
        
        # Test the popup endpoint
        r2 = requests.get(f'http://localhost:5000/api/listing-details/{listing_id}')
        print(f"Popup endpoint status: {r2.status_code}")
        
        if r2.status_code == 200:
            detail = r2.json()
            print(f"Has current: {'current' in detail}")
            print(f"Has history: {'history' in detail}")
        else:
            print(f"Error: {r2.text[:200]}")
    else:
        print("No GPU listings found")
        
except Exception as e:
    print(f"Error: {e}")
