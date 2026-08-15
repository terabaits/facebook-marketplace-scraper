import requests

print("=== Testing Admin Page ===")
try:
    r = requests.get('http://localhost:5000/admin')
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("Admin page loads OK")
        print(f"Contains '</html>': {'</html>' in r.text}")
    else:
        print(f"Error: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
