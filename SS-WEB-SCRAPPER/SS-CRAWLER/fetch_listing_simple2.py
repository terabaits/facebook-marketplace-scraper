"""Fetch and display raw listing content for debugging."""
import requests
from bs4 import BeautifulSoup

url = "https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    # Save raw HTML
    with open('listing_pbdhn_raw.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"Status: {response.status_code}")
    
    # Parse
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get title
    title = soup.find('h2', class_='msg_title')
    if title:
        title_text = title.get_text(strip=True)
        with open('listing_title.txt', 'w', encoding='utf-8') as f:
            f.write(title_text)
    
    # Get body
    body = soup.find('div', id='msg_div_msg')
    if body:
        text = body.get_text(separator=' ', strip=True)
        # Save full text
        with open('listing_pbdhn_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Saved listing_pbdhn_text.txt")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
