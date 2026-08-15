#!/usr/bin/env python3
"""Test Andele API to get all listings."""
import requests
import json

# API endpoint from the HTML
url = "https://www.andelemandele.lv/product-data/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'lv,en-US;q=0.7,en;q=0.3',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.andelemandele.lv/perles/tehnika/datori/',
}

# Try different payloads
payloads = [
    # Try with category filter
    {'category': 'datori', 'attributes': '409', 'limit': 100},
    # Try without filter
    {'limit': 100},
    # Try with page
    {'category': 'datori', 'page': 1, 'limit': 100},
]

for i, payload in enumerate(payloads):
    print(f"\n{'='*50}")
    print(f"Attempt {i+1}: {payload}")
    print('='*50)
    
    try:
        response = requests.get(url, headers=headers, params=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            # Try to parse as JSON
            try:
                data = response.json()
                print(f"Response structure: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Keys: {list(data.keys())[:10]}")
                    if 'data' in data:
                        items = data['data']
                        print(f"Number of items in 'data': {len(items)}")
                    elif 'products' in data:
                        items = data['products']
                        print(f"Number of items in 'products': {len(items)}")
                    elif 'listings' in data:
                        items = data['listings']
                        print(f"Number of items in 'listings': {len(items)}")
                    else:
                        # Print first few keys with their types
                        for key, value in list(data.items())[:5]:
                            print(f"  {key}: {type(value)} = {str(value)[:100]}")
                elif isinstance(data, list):
                    print(f"Number of items: {len(data)}")
                    if len(data) > 0:
                        print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                
                # Save response
                with open(f'andele_api_response_{i+1}.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Saved to: andele_api_response_{i+1}.json")
                
            except Exception as e:
                print(f"Failed to parse JSON: {e}")
                print(f"First 500 chars: {response.text[:500]}")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"Request failed: {e}")

print("\n\nDone!")
