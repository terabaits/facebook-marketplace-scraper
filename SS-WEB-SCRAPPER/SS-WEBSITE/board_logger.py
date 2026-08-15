"""Project Board Logger - Tracks all changes to the project board."""

import json
import os
from datetime import datetime

LOG_FILE = r'G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_board.log'

def log_action(action, task_id, details=None):
    """Log a project board action."""
    timestamp = datetime.now().isoformat()
    details_str = json.dumps(details) if details else ''
    log_entry = f"[{timestamp}] [{action}] [{task_id}] {details_str}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def log_task_created(task):
    """Log task creation."""
    log_action('CREATED', task.get('id', 'UNKNOWN'), {
        'title': task.get('title'),
        'column': task.get('column'),
        'category': task.get('category'),
        'priority': task.get('priority')
    })

def log_task_moved(task_id, from_col, to_col, user=None):
    """Log task move."""
    log_action('MOVED', task_id, {
        'from': from_col,
        'to': to_col,
        'user': user or 'system'
    })

def log_task_deleted(task_id, title=None):
    """Log task deletion."""
    log_action('DELETED', task_id, {'title': title})

def log_task_reopened(task_id, update_text):
    """Log task re-open."""
    log_action('REOPENED', task_id, {'update': update_text})

def log_task_marked_solved(task_id):
    """Log task marked as solved."""
    log_action('SOLVED', task_id, {})

def log_board_loaded(source='file'):
    """Log board load event."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [BOARD_LOADED] [SYSTEM] Source: {source}\n"
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def log_board_saved(task_count=0):
    """Log board save event."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [BOARD_SAVED] [SYSTEM] Tasks: {task_count}\n"
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def log_error(operation, error_msg):
    """Log error."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [ERROR] [{operation}] {error_msg}\n"
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def get_recent_logs(lines=50):
    """Get recent log entries."""
    try:
        if not os.path.exists(LOG_FILE):
            return []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception as e:
        return [f"Error reading log: {e}"]
