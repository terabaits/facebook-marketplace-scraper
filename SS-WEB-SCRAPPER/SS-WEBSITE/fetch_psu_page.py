import requests
import re
r = requests.get('http://localhost:5000/psus', timeout=15)
print('status', r.status_code, 'content-type', r.headers.get('content-type'))
text = r.text
imgs = re.findall(r'<img[^>]+src="([^"]+)"', text)
print('img src count', len(imgs))
for src in imgs[:10]:
    print('src:', src[:200])
print('local_image_path in page:', 'local_image_path' in text)
print('psuImgPath in page:', 'psuImgPath' in text)
