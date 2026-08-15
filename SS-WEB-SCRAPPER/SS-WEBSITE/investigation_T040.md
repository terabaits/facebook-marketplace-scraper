# Project Board Bug Investigation Report

## Issue: T040 Disappeared After Re-open

**Date:** 2026-06-19  
**Task:** T040 - "add 'Project board' to new tasks in 'Page' filter"  
**Status:** Restored to Assignment column, Bug Fixed

---

## Timeline

1. **2026-06-18 21:55:44** - T040 created in Problems column
2. **2026-06-18 21:55:49** - T040 moved to Assignment column  
3. **2026-06-19 09:14:51** - T040 marked as SOLVED (moved from talking → solved)
4. **2026-06-19 10:00:46** - T040 REOPENED with message: "everything has disappeared from the dropdown list"
5. **After reopen: T040 was GONE** - not in any column

---

## Root Cause

The `/api/project-board/reopen` endpoint had a **critical data loss vulnerability**:

```python
# Original buggy code:
for col in board['columns']:
    for t in col['tasks']:
        if t['id'] == task_id:
            task = t
            col['tasks'].remove(t)  # ← Task removed here
            break
    if task:
        break

# ... modify task ...

for col in board['columns']:
    if col['id'] == to_column:
        col['tasks'].append(task)  # ← But this might never execute!
        break

# Task is now LOST if target column not found
```

The code removes the task from its current column first, then searches for the target column. If the target column lookup fails (e.g., column ID mismatch, whitespace issues, case sensitivity), the task would be removed but never re-added.

---

## Fix Applied

Added safety check in `app.py` reopen endpoint:

1. Store original column before any changes
2. Track if target column was found
3. **If target NOT found:** Restore task to original column and log error
4. Return 400 error with informative message

```python
# Store original column for rollback if needed
original_column = task.get('column', 'solved')

# ... modify task ...

# Add to target column
target_found = False
for col in board['columns']:
    if col['id'] == to_column:
        col['tasks'].append(task)
        target_found = True
        break

# CRITICAL FIX: If target column not found, restore to original column
if not target_found:
    log_error('REOPEN', f"Target column '{to_column}' not found...")
    # Restore to original column
```

---

## T040 Status

- **Restored to:** Assignment column
- **Reopen history preserved:** Shows original reopen at 10:00:46
- **Issue reported:** "everything has disappeared from the dropdown list"

This refers to the Page dropdown in the "Add Task" modal being empty - a separate frontend issue that needs investigation.

---

## Prevention

1. **Never remove data before verifying target exists**
2. **Always have rollback logic** for destructive operations
3. **Add defensive checks** for column lookups

---

## Files Modified

- `app.py` - Fixed reopen endpoint with rollback logic
- `data/project_board.json` - Restored T040 to Assignment column
