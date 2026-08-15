import requests, re

for path in ['/motherboards', '/psus']:
    try:
        html = requests.get(f'http://localhost:5000{path}').text
        imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', html)
        print(f'=== {path} ===')
        print('Found', len(imgs), 'static img tags in initial HTML')
        for img in imgs[:10]:
            print(img)
    except Exception as e:
        print(f'Error fetching {path}: {e}')
