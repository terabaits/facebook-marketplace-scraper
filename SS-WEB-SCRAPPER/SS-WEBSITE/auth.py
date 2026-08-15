"""Authentication and authorization helpers for SS-WEBSITE."""
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify, g, redirect, request

# Lazy import of get_db_connection / app to avoid circular imports during module load
_db_conn = None
_app = None

def get_db_connection():
    global _db_conn
    if _db_conn is None:
        from app import get_db_connection as _real_get_db_connection
        _db_conn = _real_get_db_connection
    return _db_conn()

def _get_app():
    global _app
    if _app is None:
        from app import app as _real_app
        _app = _real_app
    return _app


ROLES = ['user', 'power_user', 'mod', 'admin']
ROLE_HIERARCHY = {role: idx for idx, role in enumerate(ROLES)}


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def create_user(username, password, email=None, role='user', subscription_status='inactive'):
    """Create a new user. Returns (user_id, error_message)."""
    if role not in ROLES:
        return None, f"Invalid role. Choose one of: {', '.join(ROLES)}"
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role, subscription_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            (username.strip().lower(), email, hash_password(password), role, subscription_status)
        )
        user_id = cursor.fetchone()['id']
        conn.commit()
        return user_id, None
    except psycopg2.IntegrityError as e:
        conn.rollback()
        return None, f"Username or email already exists: {e}"
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        cursor.close()
        conn.close()


def authenticate_user(username, password):
    """Verify credentials. Returns user dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = true",
            (username.strip().lower(),)
        )
        user = cursor.fetchone()
        if not user:
            return None
        if not verify_password(password, user['password_hash']):
            return None
        cursor.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = %s",
            (user['id'],)
        )
        conn.commit()
        return user
    finally:
        cursor.close()
        conn.close()


def create_session(user_id, days=30):
    """Create persistent session token."""
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(days=days)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_sessions (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (token) DO NOTHING
            RETURNING token
            """,
            (user_id, token, expires_at)
        )
        conn.commit()
        return token
    finally:
        cursor.close()
        conn.close()


def get_user_by_token(token):
    """Fetch user for a session token."""
    if not token:
        return None
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN user_sessions s ON s.user_id = u.id
            WHERE s.token = %s AND s.expires_at > NOW() AND u.is_active = true
            """,
            (token,)
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def delete_session(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_sessions WHERE token = %s", (token,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT id, username, email, role, subscription_status, subscription_tier,
                   subscription_expires_at, is_active, created_at, updated_at, last_login_at
            FROM users
            ORDER BY created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def update_user(user_id, **fields):
    """Update user fields. Allowed: email, role, subscription_status, subscription_tier,
    subscription_expires_at, is_active, password."""
    allowed = {'email', 'role', 'subscription_status', 'subscription_tier',
               'subscription_expires_at', 'is_active'}
    set_clauses = []
    params = []
    for key, value in fields.items():
        if key == 'password':
            set_clauses.append("password_hash = %s")
            params.append(hash_password(value))
        elif key in allowed:
            set_clauses.append(f"{key} = %s")
            params.append(value)
    if not set_clauses:
        return False, "No fields to update"
    set_clauses.append("updated_at = NOW()")
    params.append(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s",
            tuple(params)
        )
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()


def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def require_role(min_role):
    """Decorator: require at least min_role in hierarchy."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import g, request, jsonify, redirect
            user = g.get('current_user') or get_current_user()
            if not user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({"error": "Unauthorized"}), 401
                return redirect('/login')
            if ROLE_HIERARCHY[user['role']] < ROLE_HIERARCHY[min_role]:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import g, request, jsonify, redirect
        user = g.get('current_user') or get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def get_current_user():
    """Look up current user from session cookie or Authorization header."""
    from flask import request
    token = request.cookies.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    if not token:
        return None
    user = get_user_by_token(token)
    if user:
        from flask import g
        g.current_user = user
    return user


PAGES = [
    'index', 'gpu', 'cpu', 'computers', 'laptops', 'lenses', 'project_board',
    'models', 'admin', 'profile', 'stats'
]


def get_role_defaults(role):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT allowed_pages FROM role_page_access WHERE role = %s", (role,))
        row = cursor.fetchone()
        return row['allowed_pages'] if row else PAGES[:]
    finally:
        cursor.close()
        conn.close()


def set_role_defaults(role, allowed_pages):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO role_page_access (role, allowed_pages, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (role)
            DO UPDATE SET allowed_pages = EXCLUDED.allowed_pages, updated_at = NOW()
            """,
            (role, list(allowed_pages))
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_allowed_pages(user_id, role):
    """Combine role defaults with user-specific overrides."""
    defaults = set(get_role_defaults(role))
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT allowed_pages, denied_pages FROM user_page_access WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return defaults
        allowed = defaults | set(row['allowed_pages'] or [])
        denied = set(row['denied_pages'] or [])
        return allowed - denied
    finally:
        cursor.close()
        conn.close()


def set_user_page_access(user_id, allowed_pages=None, denied_pages=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_page_access (user_id, allowed_pages, denied_pages, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                allowed_pages = EXCLUDED.allowed_pages,
                denied_pages = EXCLUDED.denied_pages,
                updated_at = NOW()
            """,
            (user_id, list(allowed_pages or []), list(denied_pages or []))
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
