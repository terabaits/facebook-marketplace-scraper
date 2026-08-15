import requests, re

for endpoint, label in [('/api/motherboards', 'motherboards'), ('/api/psus', 'psus')]:
    r = requests.get(f'http://localhost:5000{endpoint}', timeout=15)
    print('\n---', label, 'status', r.status_code)
    try:
        data = r.json()
    except Exception as e:
        print('not json', e)
        continue
    print('items', len(data))
    if not isinstance(data, list):
        print('expected list, got', type(data))
        continue
    with_path = sum(1 for x in data if x.get('local_image_path'))
    with_url = sum(1 for x in data if x.get('image_url'))
    print('with local_image_path:', with_path)
    print('with image_url:', with_url)
    # for first 3 show keys
    for x in data[:3]:
        print(' sample', x.get('listing_id'), 'path=', x.get('local_image_path'), 'url=', x.get('image_url'))
