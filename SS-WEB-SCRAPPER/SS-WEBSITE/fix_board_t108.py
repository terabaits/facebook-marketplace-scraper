import json
from pathlib import Path

path = Path(r'G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_board.json')
with open(path, 'r', encoding='utf-8') as f:
    board = json.load(f)

now = '2026-06-26T04:35:00.000000'
t108 = None
for col in board['columns']:
    for task in col['tasks']:
        if task['id'] == 'T108':
            t108 = task

if t108:
    t108['column'] = 'talking'
    t108['fix'] = 'Reopened twice because CPU popup still showed no image. Root cause: /api/listing-details only joined gpu_reference, so CPU listings never returned cpu_name/vendor/cores/threads/socket and the popup image path was inconsistent. Fixed app.py to LEFT JOIN cpu_reference for CPU details while keeping gpu_reference for other categories. Updated templates/cpu.html showListingHistory() to show a CPU details block, source badge, and ensured the popup image uses local_image_path with fallback to image_url.'
    t108['updated'] = now
    t108['completed_at'] = now

for col in board['columns']:
    if col['id'] == 'progress':
        col['tasks'] = [t for t in col['tasks'] if t['id'] != 'T108']
    if col['id'] == 'talking':
        col['tasks'] = [t for t in col['tasks'] if t['id'] != 'T108']
        if t108:
            col['tasks'].append(t108)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(board, f, indent=2, ensure_ascii=False)

print('T108 moved to talking.')
