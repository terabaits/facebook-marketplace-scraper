import requests

response = requests.get('http://localhost:5000/api/stats')
data = response.json()

print(f"RAM key exists: {'ram' in data}")
print(f"RAM value: {data.get('ram')}")
print(f"RAM value type: {type(data.get('ram'))}")

# Also check the actual response
print(f"\nFull response RAM section:")
for key, value in data.items():
    if key == 'ram':
        print(f"  {key}: {value}")
