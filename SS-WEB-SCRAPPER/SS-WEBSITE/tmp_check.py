import urllib.request, json
from pathlib import Path
data=json.load(urllib.request.urlopen('http://localhost:5000/api/monitors?active=true'))
print('total', len(data))
Path('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/tmp_out.txt').write_text(json.dumps(data[0], indent=2), encoding='utf-8')
