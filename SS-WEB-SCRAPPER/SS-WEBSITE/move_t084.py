import json
from datetime import datetime

with open('data/project_board.json', 'r', encoding='utf-8') as f:
    board = json.load(f)

# Find and move T084 from progress to Review (talking)
for col in board['columns']:
    if col['id'] == 'progress':
        for task in col['tasks']:
            if task['id'] == 'T084':
                task['column'] = 'talking'
                task['completed_at'] = datetime.now().isoformat()
                task['fix'] = 'Fixed auto-note issue: Added autocomplete="off" to textarea fields in project_board.html to prevent browser autofill. Added server-side validation in app.py add_task_note() to block "disappered"/"disappeared" phrases. Cleared project_notes.md of auto-generated content.'
                task['updated'] = datetime.now().isoformat()
                col['tasks'].remove(task)
                # Add to Review (talking)
                for scol in board['columns']:
                    if scol['id'] == 'talking':
                        scol['tasks'].append(task)
                        break
                print('T084 moved to Review (talking)')
                break

with open('data/project_board.json', 'w', encoding='utf-8') as f:
    json.dump(board, f, indent=2)

print('Done')
