import requests, json

# Motherboards API
r = requests.get('http://localhost:5000/api/motherboards?active=true&min_confidence=0.7&time=all_time&sort=date_posted&order=desc')
data = r.json()
print('=== /api/motherboards ===')
print('status', r.status_code, 'count', len(data))
if data:
    for item in data[:5]:
        print(item.get('listing_id'), 'local_image_path:', item.get('local_image_path'), 'image_url:', item.get('image_url'))

# PSUs API
r = requests.get('http://localhost:5000/api/psus?active=true&min_confidence=0.70&time=all_time&sort=date_posted&order=desc')
data = r.json()
print('\n=== /api/psus ===')
print('status', r.status_code, 'count', len(data))
if data:
    for item in data[:5]:
        print(item.get('listing_id'), 'local_image_path:', item.get('local_image_path'), 'image_url:', item.get('image_url'))
