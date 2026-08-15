import requests

# Check lens-models API
print("=== /api/lens-models ===")
try:
    response = requests.get('http://localhost:5000/api/lens-models')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Count: {len(data) if isinstance(data, list) else 'N/A'}")
    if isinstance(data, list) and len(data) > 0:
        print(f"First item: {data[0]}")
    elif isinstance(data, dict) and 'error' in data:
        print(f"Error: {data['error']}")
    else:
        print(f"Response: {data[:3] if isinstance(data, list) else data}")
except Exception as e:
    print(f"Error: {e}")

# Check lens-details API with a sample ID
print("\n=== /api/lens-details ===")
try:
    # Use a sample lens name
    response = requests.get('http://localhost:5000/api/lens-details/Canon_50mm_f1.8_STM')
    data = response.json()
    print(f"Status: {response.status_code}")
    if 'error' in data:
        print(f"Error: {data['error']}")
    else:
        print(f"Has lens_info: {bool(data.get('lens_info'))}")
        print(f"Listings count: {len(data.get('listings', []))}")
except Exception as e:
    print(f"Error: {e}")
