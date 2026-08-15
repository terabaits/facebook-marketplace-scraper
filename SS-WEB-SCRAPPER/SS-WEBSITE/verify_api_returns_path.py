import requests
r = requests.get('http://localhost:5000/api/psus?active=false', timeout=15)
for x in r.json():
    if x.get('local_image_path'):
        print('FOUND', x['listing_id'], x.get('local_image_path'))
print('--- all paths in active=false ---')
for x in r.json():
    print(x['listing_id'], x.get('local_image_path'))
