# Find _has_no_gpu function in computer_matcher.py

with open('G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/src/scraper/computer_matcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
for i, line in enumerate(lines):
    if '_has_no_gpu' in line and 'def' in line:
        print(f"Found at line {i+1}:")
        # Print surrounding lines
        start = max(0, i-2)
        end = min(len(lines), i+20)
        for j in range(start, end):
            print(f"{j+1}: {lines[j]}", end='')
        print("\n" + "="*60)
