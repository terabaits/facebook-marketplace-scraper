import requests
r = requests.get('http://localhost:5000/images/psu/11216122_69d36d4f.jpg')
print('status', r.status_code, 'content-type', r.headers.get('content-type'), 'size', len(r.content))
