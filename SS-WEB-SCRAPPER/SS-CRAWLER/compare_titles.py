#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import psycopg2
import requests
from bs4 import BeautifulSoup

# Get DB title
conn = psycopg2.connect(
    host="localhost",
    port="5433",
    dbname="ss_market",
    user="crawler",
    password="crawler_pass"
)
cur = conn.cursor()
cur.execute("SELECT title FROM console_listings WHERE id = 205")
db_title = cur.fetchone()[0]
conn.close()

# Get live title
url = "https://www.ss.com/msg/lv/electronics/computers/game-consoles/hnoff.html"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')
title_elem = soup.find('title')
live_title = title_elem.text.split(' - ss.com')[0].strip() if title_elem else ""

print("DB Title:")
print(repr(db_title))
print()
print("Live Title:")
print(repr(live_title))
print()
print(f"Same: {db_title == live_title}")
