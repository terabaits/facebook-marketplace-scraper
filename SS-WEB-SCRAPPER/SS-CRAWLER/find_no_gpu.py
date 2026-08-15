# Search for no_gpu patterns

with open('G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src/scraper/computer_matcher.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find GPU matching section
if 'gpu' in content.lower():
    print("GPU section found")
    
# Find where GPU match is used
import re
matches = re.findall(r'gpu_match\.', content)
print(f"gpu_match references: {len(matches)}")

# Find the actual GPU matching call
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'gpu_match' in line and 'self' in line:
        print(f"Line {i+1}: {line[:80]}")
