import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/gexxm.html"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

desc = soup.find('div', id='msg_div_msg')
text = desc.get_text(separator='\n') if desc else ""

print("RAW TEXT (repr):")
print(repr(text))
print("\n" + "="*60)
print("FORMATTED TEXT:")
print(text)
