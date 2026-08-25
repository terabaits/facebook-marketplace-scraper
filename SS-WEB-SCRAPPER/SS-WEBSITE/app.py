"""SS-Crawler Web Dashboard - View scraped GPU/CPU data with statistics."""
import os
import hashlib
import json
import re
import secrets
import sys
import threading
import time as _time
from datetime import datetime, timedelta
from typing import Optional
from functools import wraps
from contextlib import contextmanager
from flask import Flask, render_template, jsonify, request, redirect, session as flask_session, g, make_response
from werkzeug.security import check_password_hash, generate_password_hash
try:
    import markdown as _markdown
except ImportError:
    _markdown = None
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from board_logger import (
    log_task_created, log_task_moved, log_task_deleted,
    log_task_reopened, log_task_marked_solved, log_board_loaded,
    log_board_saved, log_error
)

app = Flask(__name__)

# Secret key: required in production; in development fallback to a generated
# key so the app can start without the env var for convenience during local
# testing. We auto-set the dev fallback in os.environ too so subprocesses
# we spawn (e.g. start_tornado.py) inherit it without the user having to
# remember to export it first.
if 'FLASK_SECRET_KEY' in os.environ:
    app.secret_key = os.environ['FLASK_SECRET_KEY']
elif app.config.get('DEBUG') or '--debug' in sys.argv:
    # Development fallback: generate a strong 256-bit key when DEBUG is True
    # or when the app is launched directly with `python app.py --debug`.
    app.secret_key = secrets.token_hex(32)
    os.environ.setdefault('FLASK_SECRET_KEY', app.secret_key)
else:
    # Local-dev convenience: if no key is set, default to a known dev
    # key. Production deployments MUST set FLASK_SECRET_KEY to a strong
    # random value (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
    app.secret_key = 'dev-key-for-local-testing'
    os.environ['FLASK_SECRET_KEY'] = app.secret_key
    sys.stderr.write(
        'WARNING: FLASK_SECRET_KEY not set; using dev fallback. '
        'Set a strong key for production.\n'
    )

# Load translations from Jinja template for use in routes/context
_translations_cache = None

def load_translations():
    global _translations_cache
    if _translations_cache is None:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')))
        source = env.loader.get_source(env, 'translations.html')[0]
        # Extract the dict between first '{' and matching '}' before '%}'
        # Simpler: render template to evaluate set and capture via a custom global
        # Instead, parse manually using regex for the dict body
        import re, json
        match = re.search(r'{%\s*set\s+translations\s*=\s*(\{.*?\})\s*%}', source, re.DOTALL)
        if match:
            # Jinja dict literal is JSON-compatible except single quotes and trailing commas
            raw = match.group(1)
            # Replace single quotes around keys/values carefully - use ast.literal_eval
            import ast
            try:
                _translations_cache = ast.literal_eval(raw)
            except Exception:
                _translations_cache = {}
        else:
            _translations_cache = {}
    return _translations_cache


def translate(key, lang=None):
    translations = load_translations()
    if lang is None:
        lang = flask_session.get('lang', 'en')
    if lang not in translations:
        lang = 'en'
    return translations.get(lang, {}).get(key, key)


@app.context_processor
def inject_translation_helpers():
    def _t(key, lang=None):
        return translate(key, lang)
    def _translations_json():
        import json
        return json.dumps(load_translations())
    user = g.get('current_user')
    # Inject the per-user toggle defaults so listing pages can read them
    # from the template without an extra round-trip. TOGGLE_DEFINITIONS and
    # _get_toggle_role_default are defined later in this module; they're
    # available because Python evaluates all module-level code before any
    # function call.
    user_toggle_defaults = {}
    if user:
        role = user.get('role', 'user')
        for key, _label, _default, _applies_to in TOGGLE_DEFINITIONS:
            user_toggle_defaults[key] = _get_toggle_role_default(role, key)
    return dict(
        t=_t,
        translations_json=_translations_json,
        current_lang=flask_session.get('lang', 'en'),
        current_user=user,
        is_staff=bool(user and user.get('role') in ('admin', 'mod', 'moderator')),
        user_toggle_defaults=user_toggle_defaults,
        toggle_definitions=[{"key": k, "label": l, "applies_to": a, "default": d} for k, l, d, a in TOGGLE_DEFINITIONS],
    )

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 5433)),
    'database': os.environ.get('DATABASE_NAME', 'ss_market'),
    'user': os.environ.get('DATABASE_USER', 'crawler'),
    'password': os.environ.get('DATABASE_PASSWORD', 'crawler_pass')
}


# Initialize the connection pool once at startup
db_pool = pool.ThreadedConnectionPool(minconn=2, maxconn=10, **DB_CONFIG)
_pool_semaphore = threading.BoundedSemaphore(10)


# Monkey-patch RealDictCursor.execute to work around a psycopg2 bug where
# some multiline formatted SQL strings cause "tuple index out of range".
# This normalizes the query text only when the original execute raises IndexError.
_orig_real_dict_cursor_execute = RealDictCursor.execute
def _safe_execute(self, query, vars=None):
    try:
        return _orig_real_dict_cursor_execute(self, query, vars)
    except IndexError:
        normalized = query.replace('\r\n', '\n').replace('\n', ' ').replace('  ', ' ')
        return _orig_real_dict_cursor_execute(self, normalized, vars)
RealDictCursor.execute = _safe_execute


@contextmanager
def get_db_connection():
    """Yield a connection from the pool.

    A semaphore keeps the number of threads holding pool connections bounded
    by the pool size so concurrent requests queue instead of exhausting the
    pool.
    """
    _pool_semaphore.acquire()
    try:
        conn = db_pool.getconn()
        try:
            yield conn
        finally:
            db_pool.putconn(conn)
    finally:
        _pool_semaphore.release()


def cache_control(max_age=30, table='listings'):
    """Add Cache-Control and ETag headers to read-only API responses.

    ETag is generated from (MAX(updated_at) for the table, len(rows)).
    Returns 304 Not Modified when the client's If-None-Match matches.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get the latest modification timestamp from the table.
            # Fall back through common timestamp columns if updated_at is absent.
            max_ts = None
            with get_db_connection() as conn:
                cursor = conn.cursor()
                try:
                    for col in ('updated_at', 'created_at', 'first_seen_at', 'recorded_at', 'last_seen_at'):
                        try:
                            cursor.execute(f"SELECT MAX({col}) FROM {table}")
                            max_ts = cursor.fetchone()[0]
                            break
                        except Exception:
                            continue
                finally:
                    cursor.close()

            response = make_response(f(*args, **kwargs))

            # Count rows in the response payload
            try:
                data = response.get_json()
                if isinstance(data, (list, dict)):
                    row_count = len(data)
                else:
                    row_count = 0
            except Exception:
                row_count = 0

            etag_source = (str(max_ts), row_count)
            etag = hashlib.sha256(
                json.dumps(etag_source, sort_keys=True, default=str).encode()
            ).hexdigest()[:32]
            etag_header = f'"{etag}"'

            response.headers['Cache-Control'] = f'public, max-age={max_age}'
            response.headers['ETag'] = etag_header

            if request.headers.get('If-None-Match') == etag_header:
                resp304 = make_response('', 304)
                resp304.headers['Cache-Control'] = f'public, max-age={max_age}'
                resp304.headers['ETag'] = etag_header
                return resp304

            return response
        return wrapper
    return decorator


def get_role_defaults(role):
    from auth import get_role_defaults as _get_role_defaults
    return _get_role_defaults(role)



SOCKET_CHIPSETS = {
    # Intel LGA 1151 (6th/7th gen - Skylake/Kaby Lake)
    'LGA 1151': ['H110', 'B150', 'H170', 'Z170', 'B250', 'H270', 'Z270'],
    # Intel LGA 1151 v2 (8th/9th gen - Coffee Lake)
    'LGA 1151 v2': ['H310', 'B360', 'H370', 'Z370', 'B365', 'Z390'],
    # Intel LGA 1200 (10th/11th gen)
    'LGA 1200': ['H410', 'B460', 'H470', 'Z490', 'B560', 'H570', 'Z590'],
    # Intel LGA 1700 (12th/13th/14th gen)
    'LGA 1700': ['H610', 'B660', 'H670', 'Z690', 'B760', 'Z790'],
    # Intel LGA 2066 (HEDT)
    'LGA 2066': ['X299'],
    # AMD AM4
    'AM4': ['A320', 'B350', 'X370', 'B450', 'X470', 'A520', 'B550', 'X570'],
    # AMD AM5
    'AM5': ['A620', 'B650', 'X670', 'B650E', 'X670E'],
    # AMD TR4/TRX4
    'sTRX4': ['TRX40'],
    'TR4': ['X399'],
}

# Socket aliases for matching
SOCKET_ALIASES = {
    'LGA1151': 'LGA 1151',
    'LGA1151v2': 'LGA 1151 v2',
    'LGA1200': 'LGA 1200',
    'LGA1700': 'LGA 1700',
    'LGA2066': 'LGA 2066',
    'SOCKET AM4': 'AM4',
    'SOCKET AM5': 'AM5',
}

# CPU performance class mapping based on processor family/number
CPU_CLASS_MAP = {
    # Intel
    'i3': 'Budget',
    'i5': 'Mid-Range',
    'i7': 'High-End',
    'i9': 'Enthusiast',
    'xeon': 'Enthusiast',
    'pentium': 'Budget',
    'celeron': 'Budget',
    'core2': 'Budget',
    'core duo': 'Budget',
    # AMD
    'ryzen 3': 'Budget',
    'ryzen 5': 'Mid-Range',
    'ryzen 7': 'High-End',
    'ryzen 9': 'Enthusiast',
    'threadripper': 'Enthusiast',
    'athlon': 'Budget',
    'a-series': 'Budget',
    'phenom': 'Budget',
    'fx': 'Mid-Range',
}


def get_cpu_class(item):
    """Determine CPU performance class from processor_number, cpu_name, or title."""
    text = ' '.join(filter(None, [item.get('processor_number', ''), item.get('cpu_name', '')])).lower()
    # Check explicit family tokens first (even when combined text is empty)
    for token, cls in CPU_CLASS_MAP.items():
        if token in text:
            return cls

    # Generic fallback: count cores
    cores = item.get('cores')
    try:
        cores = int(cores)
    except (TypeError, ValueError):
        cores = None
    if cores is not None:
        if cores <= 4:
            return 'Budget'
        elif cores <= 6:
            return 'Mid-Range'
        elif cores <= 8:
            return 'High-End'
        else:
            return 'Enthusiast'

    # Fallback from title: extract common family tokens when cpu_name is missing
    title = (item.get('title') or '').lower()
    title_tokens = {
        'ryzen 3': 'Budget',
        'ryzen 5': 'Mid-Range',
        'ryzen 7': 'High-End',
        'ryzen 9': 'Enthusiast',
        'threadripper': 'Enthusiast',
        'athlon': 'Budget',
        'i3': 'Budget',
        'i5': 'Mid-Range',
        'i7': 'High-End',
        'i9': 'Enthusiast',
        'xeon': 'Enthusiast',
    }
    for token, cls in title_tokens.items():
        if token in title:
            return cls

    return 'Unknown'


def get_category_latest_import_date(category):
    """Get the latest import date for a specific category."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAX(first_seen_at::date) as latest_date
                FROM listings
                WHERE category = %s
            """, (category,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        finally:
            cursor.close()


def is_listing_new(listing_date, category):
    """Check if a listing is 'new' (from the latest import date for its category)."""
    if not listing_date:
        return False
    latest_import = get_category_latest_import_date(category)
    if not latest_import:
        return False
    # Compare just the date parts
    listing_date_only = listing_date.date() if hasattr(listing_date, 'date') else listing_date
    return listing_date_only == latest_import


# Configure additional static file serving for downloaded images
# Two env vars:
#   IMAGES_BASE_PATH    — the directory containing category subfolders
#                         (gpu/, cpu/, ssd/, ...). Defaults to the dev
#                         SS-CRAWLER/images path.
#   FACEBOOK_IMAGES_PATH — the directory containing the Facebook extension
#                         images. On dev this lives one level up under
#                         <project>/images/facebook; on the server set it
#                         to the same dir as IMAGES_BASE_PATH so all images
#                         can be in one volume.
_IMAGES_BASE = os.environ.get(
    'IMAGES_BASE_PATH',
    'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images',  # dev default
)
_FACEBOOK_BASE = os.environ.get(
    'FACEBOOK_IMAGES_PATH',
    'G:/Github/SS-WEB-SCRAPPER/images/facebook',  # dev default
)

IMAGE_FOLDERS = {
    'facebook': _FACEBOOK_BASE,
    'gpu': os.path.join(_IMAGES_BASE, 'gpu'),
    'gpus': os.path.join(_IMAGES_BASE, 'gpus'),
    'andele': os.path.join(_IMAGES_BASE, 'andele'),
    'andelemandele': os.path.join(_IMAGES_BASE, 'andelemandele'),
    'computer': os.path.join(_IMAGES_BASE, 'computer'),
    'computers': os.path.join(_IMAGES_BASE, 'computers'),
    'cpu': os.path.join(_IMAGES_BASE, 'cpu'),
    'cpus': os.path.join(_IMAGES_BASE, 'cpus'),
    'ram': os.path.join(_IMAGES_BASE, 'ram'),
    'rams': os.path.join(_IMAGES_BASE, 'rams'),
    'ssd': os.path.join(_IMAGES_BASE, 'ssd'),
    'ssds': os.path.join(_IMAGES_BASE, 'ssds'),
    'consoles': os.path.join(_IMAGES_BASE, 'consoles'),
    'monitor': os.path.join(_IMAGES_BASE, 'monitor'),
    'monitors': os.path.join(_IMAGES_BASE, 'monitors'),
    'cases': os.path.join(_IMAGES_BASE, 'cases'),
    'cameras': os.path.join(_IMAGES_BASE, 'cameras'),
    'lenses': os.path.join(_IMAGES_BASE, 'lenses'),
    'laptops': os.path.join(_IMAGES_BASE, 'laptops'),
    'psu': os.path.join(_IMAGES_BASE, 'psu'),
    'psus': os.path.join(_IMAGES_BASE, 'psu'),
    'motherboards': os.path.join(_IMAGES_BASE, 'motherboards'),
}

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from the external images folders."""
    from flask import send_from_directory, abort
    import os

    # Normalize path separators (handle Windows backslashes)
    filename = filename.replace('\\', '/')

    # Determine which folder to use based on filename prefix.
    # local_image_path format: "facebook/filename.jpg" or "gpus/filename.jpg" etc.
    # The stored path may use the singular folder name ("gpu/...") while the disk
    # folder is plural ("gpus"). Try the exact key first, then canonical aliases.
    folder_key = None
    actual_filename = filename

    for key in IMAGE_FOLDERS:
        if filename.startswith(f"{key}/"):
            folder_key = key
            actual_filename = filename[len(key)+1:]  # Remove the folder prefix
            break

    # If the stored prefix didn't match directly, try stripping a nested folder
    # prefix and matching against the folder keys (e.g., "gpu/filename.jpg" -> gpus).
    if folder_key is None and '/' in filename:
        parts = filename.split('/')
        for i in range(1, len(parts)):
            prefix = parts[i - 1].lower()
            candidate = '/'.join(parts[i:])
            if prefix in IMAGE_FOLDERS:
                folder_key = prefix
                actual_filename = candidate
                break
            # Also check plural/singular alias mapping.
            alias_map = {
                'gpu': 'gpu',
                'gpus': 'gpus',
                'cpu': 'cpu',
                'cpus': 'cpus',
                'ram': 'ram',
                'rams': 'rams',
                'ssd': 'ssd',
                'ssds': 'ssds',
                'psu': 'psu',
                'psus': 'psus',
                'case': 'cases',
                'cases': 'cases',
                'computer': 'computer',
                'computers': 'computers',
                'monitor': 'monitor',
                'monitors': 'monitors',
                'lens': 'lenses',
                'lenses': 'lenses',
                'laptop': 'laptops',
                'laptops': 'laptops',
                'motherboard': 'motherboards',
                'motherboards': 'motherboards',
                'camera': 'cameras',
                'cameras': 'cameras',
                'console': 'consoles',
                'consoles': 'consoles',
                'andele': 'andele',
                'andelemandele': 'andelemandele',
            }
            if prefix in alias_map and alias_map[prefix] in IMAGE_FOLDERS:
                folder_key = alias_map[prefix]
                actual_filename = candidate
                break

    if folder_key and folder_key in IMAGE_FOLDERS:
        # Some categories have both singular and plural disk folders (e.g.
        # cpu vs cpus). If the resolved folder doesn't contain the file, try
        # the alternate form so old and new stored paths both serve.
        candidates = [IMAGE_FOLDERS[folder_key]]
        alt_map = {
            'cpu': 'cpus',
            'cpus': 'cpu',
            'gpu': 'gpus',
            'gpus': 'gpu',
            'ram': 'rams',
            'rams': 'ram',
            'ssd': 'ssds',
            'ssds': 'ssd',
            'psu': 'psus',
            'psus': 'psu',
            'case': 'cases',
            'cases': 'case',
            'computer': 'computers',
            'computers': 'computer',
            'monitor': 'monitors',
            'monitors': 'monitor',
            'lens': 'lenses',
            'lenses': 'lens',
            'motherboard': 'motherboards',
            'motherboards': 'motherboard',
            'camera': 'cameras',
            'cameras': 'camera',
            'console': 'consoles',
            'consoles': 'console',
        }
        alt_key = alt_map.get(folder_key)
        if alt_key and alt_key in IMAGE_FOLDERS:
            candidates.append(IMAGE_FOLDERS[alt_key])
        for folder in candidates:
            full_path = os.path.join(folder, actual_filename)
            if os.path.exists(full_path):
                return send_from_directory(folder, actual_filename)
        # Nothing found in candidates; fall through to global fallback
        folder = IMAGE_FOLDERS[folder_key]
    else:
        # Fallback: try to find the file in any known folder.
        for key, folder in IMAGE_FOLDERS.items():
            full_path = os.path.join(folder, filename)
            if os.path.exists(full_path):
                actual_filename = os.path.basename(filename)
                return send_from_directory(folder, actual_filename)
            if '/' in filename:
                parts = filename.split('/')
                for i in range(len(parts)):
                    candidate = '/'.join(parts[i:])
                    full_path = os.path.join(folder, candidate)
                    if os.path.exists(full_path):
                        actual_filename = candidate
                        return send_from_directory(folder, actual_filename)
        return abort(404)

    return send_from_directory(folder, actual_filename)


def format_vram(vram_mb):
    """Convert VRAM from MB to GB for display (rounded half-up)."""
    if vram_mb is None:
        return None
    # Use integer half-up rounding: e.g. 512 MB -> 1 GB, matching JS Math.round.
    return (vram_mb + 512) // 1024


def get_price_changes_for_listings(cursor, listing_ids):
    """Return a mapping listing_id -> latest price_history row (with previous price)."""
    if not listing_ids:
        return {}
    cursor.execute("""
        WITH latest AS (
            SELECT
                listing_id,
                price_eur,
                recorded_at,
                LAG(price_eur) OVER (PARTITION BY listing_id ORDER BY recorded_at) AS prev_price,
                ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY recorded_at DESC) AS rn
            FROM price_history
            WHERE listing_id = ANY(%s)
        )
        SELECT listing_id, price_eur, recorded_at, prev_price
        FROM latest
        WHERE rn = 1
    """, (list(listing_ids),))
    return {row['listing_id']: dict(row) for row in cursor.fetchall()}


def detect_price_decrease(listing_dict, price_history_row):
    """Set has_price_decreased/price_changes based on the latest price history entry."""
    if not price_history_row:
        return
    latest_price = price_history_row.get('price_eur')
    prev_price = price_history_row.get('prev_price')
    if latest_price is None:
        return
    current = float(listing_dict.get('price_eur') or 0)
    latest = float(latest_price)
    compare = float(prev_price) if prev_price is not None else latest
    # If the latest history entry matches the current price, compare to the previous entry.
    if abs(current - latest) > 0.01:
        compare = latest
    if current < compare - 0.01:
        listing_dict['has_price_decreased'] = True
        change = current - compare
        listing_dict['price_changes'] = [{
            'change': float(change),
            'recorded_at': price_history_row['recorded_at'].isoformat() if price_history_row.get('recorded_at') else None
        }]


def convert_decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj


def get_time_filter_sql(time_filter, table_alias='l'):
    """Generate SQL time filter clause."""
    if time_filter == 'active':
        return f" AND {table_alias}.is_active = true"
    elif time_filter == 'week':
        return f" AND COALESCE({table_alias}.date_posted, {table_alias}.first_seen_at, {table_alias}.created_at) > NOW() - INTERVAL '7 days'"
    elif time_filter == 'month':
        return f" AND COALESCE({table_alias}.date_posted, {table_alias}.first_seen_at, {table_alias}.created_at) > NOW() - INTERVAL '30 days'"
    return ""  # all_time


def get_active_avg_clauses(request, table_alias='l'):
    """Return (time_clause, flagged_clause) tuple based on request params.

    Flagged listings are always excluded from averages because they are
    marked as bogus/wrong matches. The time_clause controls whether only
    active listings or all historical listings are used.
    """
    use_active_avg = request.args.get('use_active_avg', 'false').lower() == 'true'
    if use_active_avg:
        time_clause = f" AND {table_alias}.is_active = true"
    else:
        time_clause = ""
    flagged_clause = f" AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = {table_alias}.listing_id)"
    return time_clause, flagged_clause


@app.route('/')
def index():
    """Dashboard homepage."""
    return render_template('index.html')


@app.route('/api/category-earnings')
@cache_control(max_age=30)
def get_category_earnings():
    """Get earnings/revenue data by category."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get earnings data by category
            # Potential savings = sum of (max_price - current_price) for each listing
            cursor.execute("""
                SELECT
                    category,
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(SUM(category_max - price_eur)::numeric, 2) as potential_savings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM (
                    SELECT
                        category,
                        price_eur,
                        is_active,
                        MAX(price_eur) OVER (PARTITION BY category) as category_max
                    FROM listings
                    WHERE category IN ('gpu', 'cpu', 'ssd', 'ram', 'psu', 'case', 'motherboard', 'monitor', 'camera', 'lens', 'console')
                ) sub
                GROUP BY category
                ORDER BY potential_savings DESC
            """)

            earnings = cursor.fetchall()

            # Convert list to category-keyed map expected by the frontend
            earnings_map = {}
            for row in earnings:
                cat = row['category']
                earnings_map[cat] = {
                    'opportunity': float(row.get('potential_savings') or 0),
                    'avg_price': float(row.get('avg_price') or 0),
                    'listing_count': int(row.get('active_listings') or 0),
                    'total_listings': int(row.get('total_listings') or 0),
                    'min_price': float(row.get('min_price') or 0),
                    'max_price': float(row.get('max_price') or 0)
                }

            # Get total earnings across all categories
            cursor.execute("""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(SUM(category_max - price_eur)::numeric, 2) as total_potential_savings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price
                FROM (
                    SELECT
                        category,
                        price_eur,
                        is_active,
                        MAX(price_eur) OVER (PARTITION BY category) as category_max
                    FROM listings
                    WHERE category IN ('gpu', 'cpu', 'ssd', 'ram', 'psu', 'case', 'motherboard', 'monitor', 'camera', 'lens', 'console')
                ) sub
            """)

            totals = dict(cursor.fetchone())

            result = {
                'totals': {
                    'total_listings': int(totals.get('total_listings') or 0),
                    'active_listings': int(totals.get('active_listings') or 0),
                    'opportunity': float(totals.get('total_potential_savings') or 0),
                    'avg_price': float(totals.get('avg_price') or 0)
                },
                **earnings_map
            }

            cursor.close()

            return jsonify(result)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


def _format_model_label(category, info):
    """Format a clean human label for a model. Avoids the awkward
    "AMD AMD Ryzen 9 7900" double-brand when the cpu_name already
    includes the brand."""
    if category == 'cpu':
        brand = (info.get('brand') or info.get('producer') or '').strip()
        model = (info.get('model') or info.get('cpu_name') or '').strip()
    elif category == 'gpu':
        brand = (info.get('brand') or info.get('vendor') or '').strip()
        model = (info.get('model') or info.get('raw_model') or '').strip()
    elif category == 'ssd':
        brand = (info.get('brand') or '').strip()
        model = (info.get('model') or '').strip()
    elif category == 'ram':
        brand = ''
        model = (info.get('model') or info.get('name') or '').strip()
    else:
        brand = (info.get('brand') or '').strip()
        model = (info.get('model') or '').strip()
    if brand and model.lower().startswith(brand.lower()):
        return model
    return f"{brand} {model}".strip() if (brand or model) else f"#{info.get('id', '?')}"


@app.route('/api/model-search')
def model_search():
    """Search across gpu/cpu/ram/ssd reference tables for the dashboard
    model picker. Returns up to 25 results with id, category, label.

    Query params:
        q   — required search string (matches brand/model/name/keywords)
        cat — optional category filter (gpu/cpu/ram/ssd)
    """
    raw = (request.args.get('q') or '').strip()
    if not raw or len(raw) < 2:
        return jsonify({'results': [], 'query': raw})
    cat = (request.args.get('cat') or '').strip().lower()
    like = f'%{raw}%'
    results = []
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # gpu
        if cat in ('', 'gpu'):
            cur.execute("""
                SELECT id, vendor AS brand, model, 'gpu' AS category
                FROM gpu_reference
                WHERE model ILIKE %s OR raw_model ILIKE %s
                   OR vendor ILIKE %s OR %s = ANY(search_keywords)
                ORDER BY
                    CASE WHEN model ILIKE %s THEN 0
                         WHEN raw_model ILIKE %s THEN 1
                         ELSE 2 END,
                    model
                LIMIT 25
            """, (like, like, like, raw.lower(), raw + '%', raw + '%'))
            for r in cur.fetchall():
                results.append({'id': r['id'], 'category': r['category'],
                                'label': _format_model_label('gpu', dict(r))})
        # cpu
        if cat in ('', 'cpu'):
            cur.execute("""
                SELECT id, producer AS brand, cpu_name AS model, 'cpu' AS category
                FROM cpu_reference
                WHERE cpu_name ILIKE %s OR producer ILIKE %s
                   OR processor_number ILIKE %s
                   OR %s = ANY(search_keywords)
                ORDER BY
                    CASE WHEN cpu_name ILIKE %s THEN 0
                         WHEN processor_number ILIKE %s THEN 1
                         ELSE 2 END,
                    cpu_name
                LIMIT 25
            """, (like, like, like, raw.lower(), raw + '%', raw + '%'))
            for r in cur.fetchall():
                results.append({'id': r['id'], 'category': r['category'],
                                'label': _format_model_label('cpu', dict(r))})
        # ram
        if cat in ('', 'ram'):
            cur.execute("""
                SELECT id, '' AS brand, name AS model, speed, capacity_gb, 'ram' AS category
                FROM ram_reference
                WHERE name ILIKE %s
                   OR %s = ANY(search_keywords)
                ORDER BY
                    CASE WHEN name ILIKE %s THEN 0 ELSE 1 END,
                    name
                LIMIT 25
            """, (like, raw.lower(), raw + '%'))
            for r in cur.fetchall():
                bits = [r['model']]
                if r.get('speed'):
                    bits.append(str(r['speed']))
                if r.get('capacity_gb'):
                    bits.append(f"{r['capacity_gb']} GB")
                label = ' '.join(bits).strip()
                results.append({'id': r['id'], 'category': r['category'], 'label': label})
        # ssd
        if cat in ('', 'ssd'):
            cur.execute("""
                SELECT id, brand, model, capacity_gb, 'ssd' AS category
                FROM ssd_reference
                WHERE model ILIKE %s OR brand ILIKE %s
                   OR %s = ANY(search_keywords)
                ORDER BY
                    CASE WHEN model ILIKE %s THEN 0
                         WHEN brand ILIKE %s THEN 1
                         ELSE 2 END,
                    model
                LIMIT 25
            """, (like, like, raw.lower(), raw + '%', raw + '%'))
            for r in cur.fetchall():
                bits = [r['brand'], r['model']]
                if r.get('capacity_gb'):
                    bits.append(f"{r['capacity_gb']} GB")
                label = ' '.join(b for b in bits if b).strip()
                results.append({'id': r['id'], 'category': r['category'], 'label': label})
    # Sort: best label match first, then alphabetical. Cap at 50 total.
    results = results[:50]
    return jsonify({'results': results, 'query': raw, 'count': len(results)})


# In-process cache for the dashboard summary. Keyed on the filter
# signature; values are (timestamp, response) tuples. Rapid chip clicks
# coalesce into one DB round-trip per filter combo per 3-second window.
_DASH_CACHE = {}
_DASH_CACHE_LOCK = threading.Lock()


@app.route('/api/dashboard-summary')
def get_dashboard_summary():
    """Dashboard summary. The full SQL touches the entire listings +
    price_history tables and takes ~2s; rapid chip clicks would otherwise
    pile up concurrent 2s queries. We memoize the JSON payload for 3
    seconds so a burst of clicks coalesces into one DB hit per filter
    combo. We store the JSON body (not the Response object) so each
    request builds a fresh Response — sharing a Response across requests
    would consume the body and the second call would return empty.
    """
    cache_key = (
        tuple(sorted(c for c in request.args.get('categories', '').split(',') if c)),
        request.args.get('model_id', '').strip(),
        request.args.get('category', '').strip(),
    )
    now = _time.time()
    with _DASH_CACHE_LOCK:
        cached = _DASH_CACHE.get(cache_key)
    if cached and now - cached[0] < 3.0:
        return _cached_dash_response(cached[1])
    response = _dashboard_summary_impl()
    # Only cache successful responses (Response with 200).
    try:
        if hasattr(response, 'status_code') and response.status_code == 200:
            payload = response.get_data(as_text=True)
            with _DASH_CACHE_LOCK:
                _DASH_CACHE[cache_key] = (now, payload)
                # Prune stale entries opportunistically
                if len(_DASH_CACHE) > 32:
                    stale = [k for k, v in _DASH_CACHE.items() if now - v[0] > 30]
                    for k in stale:
                        del _DASH_CACHE[k]
    except Exception:
        pass
    return response


def _cached_dash_response(json_payload):
    """Build a fresh Response from a cached JSON string. Reusing the
    same Response object across requests would consume the body once
    and the second call would return empty."""
    from flask import Response
    resp = Response(json_payload, status=200, mimetype='application/json')
    return resp


def _dashboard_summary_impl():
    """One-shot payload for the redesigned dashboard.

    Returns per-category stats, total opportunity (3 flavours: max-upside,
    haggling, and "as-is vs. all-time max"), top deals, top price drops,
    category totals, and a 30-day new-listing activity series.

    Optional filters (querystring):
        ?categories=gpu,cpu   — restrict to these categories (default: all)
        ?model_id=343         — restrict to one specific matched model
                                (overrides the categories filter for the
                                 per-model sections; totals stay category-wide)
        ?category=cpu         — disambiguate which ref table to probe
                                (model IDs collide across gpu/cpu/ram/ssd)
    The dashboard always excludes flagged and unmatched listings.
    """
    # Parse the page/category filter
    raw_cats = request.args.get('categories', '').strip()
    selected_cats = [c.strip() for c in raw_cats.split(',') if c.strip()] if raw_cats else []
    valid_cats = {'gpu','cpu','ssd','ram','psu','case','motherboard','monitor','camera','lens','console'}
    if selected_cats:
        selected_cats = [c for c in selected_cats if c in valid_cats]
        if not selected_cats:
            selected_cats = list(valid_cats)  # all invalid → fall back to all
    else:
        selected_cats = list(valid_cats)

    cats_sql = ','.join(f"'{c}'" for c in selected_cats)
    cats_in_list = '(' + cats_sql + ')'

    # Parse the model filter (single model ID — restricts to listings that
    # matched this model). The model is per-category, so we discover the
    # model category from the DB. A ?category= hint picks the right probe
    # first when the id collides across reference tables.
    model_id_raw = request.args.get('model_id', '').strip()
    model_id = int(model_id_raw) if model_id_raw.isdigit() else None
    model_cat_hint = request.args.get('category', '').strip().lower()
    if model_cat_hint not in valid_cats:
        model_cat_hint = ''

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # If a model_id is given, discover which category it belongs to
            # and which ID column to filter on. We probe each reference table
            # in order — they all have integer IDs. Different tables use
            # different name columns; we pick the right one for each.
            model_filter = None  # (matched_column_name, category, info_dict) or None
            if model_id is not None:
                # (column_for_id_match, category, info_columns)
                ref_probes = [
                    # gpu_reference: (id, model, raw_model)
                    ('matched_gpu_id', 'gpu', "id, model, raw_model", "gpu_reference", "gpu"),
                    # cpu_reference: (id, producer, cpu_name)
                    ('matched_cpu_id', 'cpu', "id, producer AS brand, cpu_name AS model", "cpu_reference", "cpu"),
                    # ram_reference: (id, name)
                    ('matched_ram_id', 'ram', "id, '' AS brand, name AS model", "ram_reference", "ram"),
                    # ssd_reference: (id, brand, model)
                    ('matched_ssd_id', 'ssd', "id, brand, model", "ssd_reference", "ssd"),
                ]
                # If a ?category= hint was given, try that probe first so
                # the model_id collision across tables resolves correctly.
                if model_cat_hint:
                    order_map = {
                        'gpu': 0, 'cpu': 1, 'ram': 2, 'ssd': 3,
                    }
                    if model_cat_hint in order_map:
                        hint_idx = order_map[model_cat_hint]
                        ref_probes.insert(0, ref_probes.pop(hint_idx))
                for matched_col, cat, cols, tbl, _ in ref_probes:
                    # NOTE: cursor.execute() returns None in psycopg2; the
                    # result lives on the cursor. Calling .fetchone() on the
                    # return value raises "'NoneType' object has no attribute
                    # 'fetchone'".
                    cursor.execute(
                        f"SELECT {cols} FROM {tbl} WHERE id = %s", (model_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        model_filter = (matched_col, cat, dict(row))
                        break
                if model_filter:
                    # Override the categories filter — the model filter
                    # implies its own category
                    selected_cats = [model_filter[1]]
                    cats_sql = f"'{model_filter[1]}'"
                    cats_in_list = '(' + cats_sql + ')'
            # When a model filter is active, restrict the per-listing queries
            # to rows that matched that specific model. Skipped when the
            # user didn't pass model_id (or it's invalid).
            model_filter_sql = ''
            if model_filter is not None:
                _col = model_filter[0]
                model_filter_sql = f""" AND l.{_col} = {model_filter[2]['id']} """
            if model_filter is None:
                model_filter_sql = ''


            # Per-category stats: count, avg, min, max, total value,
            # "max upside" = sum(max_ever - current) for active listings,
            # "haggle" = sum(max_ever - min_ever) (theoretical perfect trade).
            # Excludes flagged listings and unmatched listings so the dashboard
            # only reflects the "clean" view of inventory.
            cursor.execute(f"""
                WITH base AS (
                    SELECT
                        l.category,
                        l.price_eur AS current_price,
                        l.is_active,
                        l.listing_id,
                        l.title,
                        l.image_url,
                        l.listing_url,
                        MAX(l.price_eur) OVER (PARTITION BY l.category) AS cat_max,
                        MIN(l.price_eur) OVER (PARTITION BY l.category) AS cat_min
                    FROM listings l
                    WHERE l.category IN {cats_in_list} {model_filter_sql}
                      AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                      AND (
                          l.matched_cpu_id IS NOT NULL OR
                          l.matched_gpu_id IS NOT NULL OR
                          l.matched_ram_id IS NOT NULL OR
                          l.matched_ssd_id IS NOT NULL OR
                          l.matched_psu_id IS NOT NULL OR
                          l.matched_case_id IS NOT NULL OR
                          l.matched_camera_id IS NOT NULL OR
                          l.matched_lens_id IS NOT NULL OR
                          l.matched_console_id IS NOT NULL OR
                          l.monitor_model_id IS NOT NULL OR
                          l.motherboard_model_id IS NOT NULL
                      )
                )
                SELECT
                    category,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_active) AS active,
                    ROUND(AVG(current_price)::numeric, 2) AS avg_price,
                    MIN(current_price) AS min_price,
                    MAX(current_price) AS max_price,
                    ROUND(SUM(current_price) FILTER (WHERE is_active)::numeric, 2) AS active_value,
                    ROUND(SUM(GREATEST(cat_max - current_price, 0)) FILTER (WHERE is_active)::numeric, 2) AS upside_max,
                    ROUND(SUM(GREATEST(cat_max - cat_min, 0))::numeric, 2) AS haggling_max
                FROM base
                GROUP BY category
                ORDER BY upside_max DESC NULLS LAST
            """)
            cats = cursor.fetchall()
            categories = []
            for r in cats:
                avg = float(r.get('avg_price') or 0)
                active = int(r.get('active') or 0)
                categories.append({
                    "category": r["category"],
                    "total": int(r.get("total") or 0),
                    "active": active,
                    "avg_price": avg,
                    "min_price": float(r.get("min_price") or 0),
                    "max_price": float(r.get("max_price") or 0),
                    "active_value": float(r.get("active_value") or 0),
                    "upside_max": float(r.get("upside_max") or 0),
                    "haggling_max": float(r.get("haggling_max") or 0),
                    "vs_avg_per_listing": (float(r.get("upside_max") or 0) / active) if active else 0,
                })

            # Totals — same exclusion as the per-category CTE above so
            # the dashboard never counts flagged or unmatched listings.
            # Also applies model_filter_sql so picking a model (e.g.
            # "i7-6700") shows the correct subset instead of the
            # full database totals. Without the filter clause, a
            # model-filtered view would show 83 active listings
            # even when only 5 listings match that model.
            # NOTE: table aliased as `l` because model_filter_sql
            # references `l.matched_cpu_id` (etc.) — the other
            # queries in this file use the same convention.
            cursor.execute(f"""
                SELECT
                    COUNT(*) AS total_listings,
                    COUNT(*) FILTER (WHERE l.is_active) AS active_listings,
                    COUNT(DISTINCT l.category) AS categories_with_listings,
                    ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price,
                    ROUND(SUM(l.price_eur) FILTER (WHERE l.is_active)::numeric, 2) AS active_value
                FROM listings l
                WHERE l.category IN {cats_in_list} {model_filter_sql}
                  AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                  AND (
                      l.matched_cpu_id IS NOT NULL OR
                      l.matched_gpu_id IS NOT NULL OR
                      l.matched_ram_id IS NOT NULL OR
                      l.matched_ssd_id IS NOT NULL OR
                      l.matched_psu_id IS NOT NULL OR
                      l.matched_case_id IS NOT NULL OR
                      l.matched_camera_id IS NOT NULL OR
                      l.matched_lens_id IS NOT NULL OR
                      l.matched_console_id IS NOT NULL OR
                      l.monitor_model_id IS NOT NULL OR
                      l.motherboard_model_id IS NOT NULL
                  )
            """)
            totals = dict(cursor.fetchone())

            # Biggest % deals: listing's current price vs category avg
            cursor.execute(f"""
                WITH stats AS (
                    SELECT
                        l.listing_id, l.title, l.category, l.price_eur,
                        l.image_url, l.listing_url,
                        AVG(l.price_eur) OVER (PARTITION BY l.category) AS ref_avg,
                        MIN(l.price_eur) OVER (PARTITION BY l.category) AS ref_min
                    FROM listings l
                    WHERE l.is_active = true
                      AND l.category IN {cats_in_list} {model_filter_sql}
                      AND l.price_eur > 0
                      AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                      AND (
                          l.matched_cpu_id IS NOT NULL OR
                          l.matched_gpu_id IS NOT NULL OR
                          l.matched_ram_id IS NOT NULL OR
                          l.matched_ssd_id IS NOT NULL OR
                          l.matched_psu_id IS NOT NULL OR
                          l.matched_case_id IS NOT NULL OR
                          l.matched_camera_id IS NOT NULL OR
                          l.matched_lens_id IS NOT NULL OR
                          l.matched_console_id IS NOT NULL OR
                          l.monitor_model_id IS NOT NULL OR
                          l.motherboard_model_id IS NOT NULL
                      )
                )
                SELECT *,
                    ROUND(((ref_avg - price_eur) / ref_avg * 100)::numeric, 1) AS pct_below_avg,
                    ROUND((ref_avg - price_eur)::numeric, 2) AS below_avg_eur
                FROM stats
                WHERE ref_avg > 0
                ORDER BY ((ref_avg - price_eur) / ref_avg) DESC NULLS LAST
                LIMIT 10
            """)
            top_deals = []
            for r in cursor.fetchall():
                top_deals.append({
                    "listing_id": r["listing_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "price_eur": float(r["price_eur"]),
                    "image_url": r.get("image_url"),
                    "listing_url": r.get("listing_url"),
                    "ref_avg": float(r["ref_avg"] or 0),
                    "ref_min": float(r["ref_min"] or 0),
                    "pct_below_avg": float(r.get("pct_below_avg") or 0),
                    "below_avg_eur": float(r.get("below_avg_eur") or 0),
                })

            # Biggest absolute price drops (vs previous price in price_history)
            cursor.execute(f"""
                SELECT
                    l.listing_id, l.title, l.category, l.price_eur AS current_price,
                    l.image_url, l.listing_url,
                    ph.price_eur AS old_price,
                    (ph.price_eur - l.price_eur) AS drop_eur,
                    CASE WHEN ph.price_eur > 0
                         THEN ROUND(((ph.price_eur - l.price_eur) / ph.price_eur * 100)::numeric, 1)
                         ELSE 0 END AS drop_pct,
                    ph.recorded_at
                FROM listings l
                JOIN LATERAL (
                    SELECT price_eur, recorded_at
                    FROM price_history ph
                    WHERE ph.listing_id = l.listing_id
                    ORDER BY recorded_at DESC
                    LIMIT 1
                ) ph ON true
                WHERE l.is_active = true
                  AND l.category IN {cats_in_list} {model_filter_sql}
                ORDER BY (ph.price_eur - l.price_eur) DESC
                LIMIT 10
            """)
            top_drops = []
            for r in cursor.fetchall():
                top_drops.append({
                    "listing_id": r["listing_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "current_price": float(r["current_price"]),
                    "old_price": float(r["old_price"]),
                    "drop_eur": float(r["drop_eur"]),
                    "drop_pct": float(r.get("drop_pct") or 0),
                    "image_url": r.get("image_url"),
                    "listing_url": r.get("listing_url"),
                    "recorded_at": r["recorded_at"].isoformat() if r.get("recorded_at") else None,
                })

            # Biggest absolute price RISES (for completeness)
            cursor.execute(f"""
                SELECT
                    l.listing_id, l.title, l.category, l.price_eur AS current_price,
                    ph.price_eur AS old_price,
                    (l.price_eur - ph.price_eur) AS rise_eur
                FROM listings l
                JOIN LATERAL (
                    SELECT price_eur FROM price_history ph
                    WHERE ph.listing_id = l.listing_id
                    ORDER BY recorded_at DESC LIMIT 1
                ) ph ON true
                WHERE l.is_active = true
                  AND l.category IN {cats_in_list} {model_filter_sql}
                  AND l.price_eur > ph.price_eur
                  AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                ORDER BY (l.price_eur - ph.price_eur) DESC
                LIMIT 10
            """)
            top_rises = [
                {
                    "listing_id": r["listing_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "current_price": float(r["current_price"]),
                    "old_price": float(r["old_price"]),
                    "rise_eur": float(r["rise_eur"]),
                } for r in cursor.fetchall()
            ]

            # 30-day new-listing activity
            cursor.execute(f"""
                SELECT
                    DATE(first_seen_at) AS day,
                    COUNT(*) AS new_listings
                FROM listings
                WHERE first_seen_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(first_seen_at)
                ORDER BY day
            """)
            activity = [
                {"day": r["day"].isoformat(), "count": int(r["new_listings"])}
                for r in cursor.fetchall()
            ]

            # Per-category match rates (handle monitor_model_id / motherboard_model_id too).
            # Excludes flagged listings from both total and matched counts.
            cursor.execute(f"""
                SELECT
                    category,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE matched_cpu_id IS NOT NULL
                                      OR matched_gpu_id IS NOT NULL
                                      OR matched_ram_id IS NOT NULL
                                      OR matched_ssd_id IS NOT NULL
                                      OR matched_psu_id IS NOT NULL
                                      OR matched_case_id IS NOT NULL
                                      OR matched_camera_id IS NOT NULL
                                      OR matched_lens_id IS NOT NULL
                                      OR matched_console_id IS NOT NULL
                                      OR monitor_model_id IS NOT NULL
                                      OR motherboard_model_id IS NOT NULL) AS matched
                FROM listings
                WHERE category IN {cats_in_list}
                  AND listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                GROUP BY category
            """)
            match_rates = {r["category"]: {
                "total": int(r["total"] or 0),
                "matched": int(r["matched"] or 0),
                "rate": round((int(r["matched"] or 0) / int(r["total"] or 1)) * 100, 1)
                          if r["total"] else 0
            } for r in cursor.fetchall()}

            # === PER-MODEL aggregations: highest/lowest price ever for each model ===
            # We group by category + the matching model id column, take max/min across
            # ALL listings (active + inactive) plus all rows in price_history.
            # Then join back to active listings to find the per-listing "vs model max" gap.
            cursor.execute(f"""
                WITH model_agg AS (
                    SELECT 'gpu' AS category, matched_gpu_id::text AS model_id, MAX(price_eur) AS model_max, MIN(price_eur) AS model_min, COUNT(*) AS model_listings
                    FROM listings WHERE matched_gpu_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_gpu_id
                    UNION ALL SELECT 'cpu', matched_cpu_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_cpu_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_cpu_id
                    UNION ALL SELECT 'ram', matched_ram_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_ram_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_ram_id
                    UNION ALL SELECT 'ssd', matched_ssd_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_ssd_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_ssd_id
                    UNION ALL SELECT 'psu', matched_psu_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_psu_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_psu_id
                    UNION ALL SELECT 'case', matched_case_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_case_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_case_id
                    UNION ALL SELECT 'lens', matched_lens_id, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_lens_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_lens_id
                    UNION ALL SELECT 'camera', matched_camera_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_camera_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_camera_id
                    UNION ALL SELECT 'console', matched_console_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_console_id IS NOT NULL AND price_eur > 0
                    GROUP BY matched_console_id
                    UNION ALL SELECT 'monitor', monitor_model_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE monitor_model_id IS NOT NULL AND price_eur > 0
                    GROUP BY monitor_model_id
                    UNION ALL SELECT 'motherboard', motherboard_model_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE motherboard_model_id IS NOT NULL AND price_eur > 0
                    GROUP BY motherboard_model_id
                ),
                cat_rollup AS (
                    SELECT category,
                           COUNT(DISTINCT model_id) AS unique_models,
                           ROUND(AVG(model_max)::numeric, 2) AS avg_model_max,
                           ROUND(AVG(model_min)::numeric, 2) AS avg_model_min,
                           SUM(model_max - model_min) AS haggling_potential
                    FROM model_agg
                    GROUP BY category
                )
                SELECT * FROM cat_rollup
            """)
            model_stats = {r["category"]: {
                "unique_models": int(r["unique_models"] or 0),
                "avg_model_max": float(r["avg_model_max"] or 0),
                "avg_model_min": float(r["avg_model_min"] or 0),
                "haggling_potential": float(r["haggling_potential"] or 0),
            } for r in cursor.fetchall()}

            # === Top "buy signals" — active listings priced significantly below their
            # model's all-time max. This is the "if you can get this model at the current
            # price, you could sell for up to model_max" view. ===
            cursor.execute(f"""
                WITH model_agg AS (
                    SELECT 'gpu' AS category, matched_gpu_id::text AS model_id, MAX(price_eur) AS model_max
                    FROM listings WHERE matched_gpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_gpu_id
                    UNION ALL SELECT 'cpu', matched_cpu_id::text, MAX(price_eur) FROM listings WHERE matched_cpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_cpu_id
                    UNION ALL SELECT 'ram', matched_ram_id::text, MAX(price_eur) FROM listings WHERE matched_ram_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ram_id
                    UNION ALL SELECT 'ssd', matched_ssd_id::text, MAX(price_eur) FROM listings WHERE matched_ssd_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ssd_id
                    UNION ALL SELECT 'psu', matched_psu_id::text, MAX(price_eur) FROM listings WHERE matched_psu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_psu_id
                    UNION ALL SELECT 'case', matched_case_id::text, MAX(price_eur) FROM listings WHERE matched_case_id IS NOT NULL AND price_eur > 0 GROUP BY matched_case_id
                    UNION ALL SELECT 'lens', matched_lens_id, MAX(price_eur) FROM listings WHERE matched_lens_id IS NOT NULL AND price_eur > 0 GROUP BY matched_lens_id
                    UNION ALL SELECT 'camera', matched_camera_id::text, MAX(price_eur) FROM listings WHERE matched_camera_id IS NOT NULL AND price_eur > 0 GROUP BY matched_camera_id
                    UNION ALL SELECT 'console', matched_console_id::text, MAX(price_eur) FROM listings WHERE matched_console_id IS NOT NULL AND price_eur > 0 GROUP BY matched_console_id
                    UNION ALL SELECT 'monitor', monitor_model_id::text, MAX(price_eur) FROM listings WHERE monitor_model_id IS NOT NULL AND price_eur > 0 GROUP BY monitor_model_id
                    UNION ALL SELECT 'motherboard', motherboard_model_id::text, MAX(price_eur) FROM listings WHERE motherboard_model_id IS NOT NULL AND price_eur > 0 GROUP BY motherboard_model_id
                ),
                per_listing AS (
                    SELECT l.listing_id, l.title, l.category, l.price_eur, l.image_url, l.listing_url,
                           ma.model_max, (ma.model_max - l.price_eur) AS upside_eur,
                           CASE WHEN ma.model_max > 0
                                THEN ROUND(((ma.model_max - l.price_eur) / ma.model_max * 100)::numeric, 1)
                                ELSE 0 END AS upside_pct
                    FROM listings l
                    JOIN model_agg ma ON ma.category = l.category
                        AND (
                            (l.category='gpu'        AND ma.model_id = l.matched_gpu_id::text)        OR
                            (l.category='cpu'        AND ma.model_id = l.matched_cpu_id::text)        OR
                            (l.category='ram'        AND ma.model_id = l.matched_ram_id::text)        OR
                            (l.category='ssd'        AND ma.model_id = l.matched_ssd_id::text)        OR
                            (l.category='psu'        AND ma.model_id = l.matched_psu_id::text)        OR
                            (l.category='case'       AND ma.model_id = l.matched_case_id::text)       OR
                            (l.category='lens'       AND ma.model_id = l.matched_lens_id)             OR
                            (l.category='camera'     AND ma.model_id = l.matched_camera_id::text)     OR
                            (l.category='console'    AND ma.model_id = l.matched_console_id::text)    OR
                            (l.category='monitor'    AND ma.model_id = l.monitor_model_id::text)      OR
                            (l.category='motherboard'AND ma.model_id = l.motherboard_model_id::text)
                        )
                    WHERE l.is_active = true AND l.price_eur > 0
                      AND l.category IN {cats_in_list} {model_filter_sql}
                      AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                )
                SELECT * FROM per_listing
                WHERE upside_eur > 0
                ORDER BY upside_eur DESC
                LIMIT 10
            """)
            top_buy_signals = []
            for r in cursor.fetchall():
                top_buy_signals.append({
                    "listing_id": r["listing_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "price_eur": float(r["price_eur"]),
                    "image_url": r.get("image_url"),
                    "listing_url": r.get("listing_url"),
                    "model_max": float(r["model_max"]),
                    "upside_eur": float(r["upside_eur"]),
                    "upside_pct": float(r.get("upside_pct") or 0),
                })

            # === Per-model max upside: "highest price each model has ever been sold"
            # This is the user's exact ask: for every model, find the highest price
            # that specific model has ever been listed at. Then for each active
            # listing, the gap (model_max - current) is what the user could capture
            # if they bought and resold at the model's all-time max.
            cursor.execute(f"""
                WITH model_agg AS (
                    SELECT 'gpu' AS category, matched_gpu_id::text AS model_id, MAX(price_eur) AS model_max, MIN(price_eur) AS model_min
                    FROM listings WHERE matched_gpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_gpu_id
                    UNION ALL SELECT 'cpu', matched_cpu_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_cpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_cpu_id
                    UNION ALL SELECT 'ram', matched_ram_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_ram_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ram_id
                    UNION ALL SELECT 'ssd', matched_ssd_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_ssd_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ssd_id
                    UNION ALL SELECT 'psu', matched_psu_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_psu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_psu_id
                    UNION ALL SELECT 'case', matched_case_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_case_id IS NOT NULL AND price_eur > 0 GROUP BY matched_case_id
                    UNION ALL SELECT 'lens', matched_lens_id, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_lens_id IS NOT NULL AND price_eur > 0 GROUP BY matched_lens_id
                    UNION ALL SELECT 'camera', matched_camera_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_camera_id IS NOT NULL AND price_eur > 0 GROUP BY matched_camera_id
                    UNION ALL SELECT 'console', matched_console_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE matched_console_id IS NOT NULL AND price_eur > 0 GROUP BY matched_console_id
                    UNION ALL SELECT 'monitor', monitor_model_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE monitor_model_id IS NOT NULL AND price_eur > 0 GROUP BY monitor_model_id
                    UNION ALL SELECT 'motherboard', motherboard_model_id::text, MAX(price_eur), MIN(price_eur) FROM listings WHERE motherboard_model_id IS NOT NULL AND price_eur > 0 GROUP BY motherboard_model_id
                ),
                per_listing AS (
                    SELECT l.listing_id, l.title, l.category, l.price_eur, l.image_url, l.listing_url,
                           ma.model_max, (ma.model_max - l.price_eur) AS upside_eur,
                           ma.model_min, (ma.model_max - ma.model_min) AS haggling_eur
                    FROM listings l
                    JOIN model_agg ma ON ma.category = l.category
                        AND (
                            (l.category='gpu'        AND ma.model_id = l.matched_gpu_id::text)        OR
                            (l.category='cpu'        AND ma.model_id = l.matched_cpu_id::text)        OR
                            (l.category='ram'        AND ma.model_id = l.matched_ram_id::text)        OR
                            (l.category='ssd'        AND ma.model_id = l.matched_ssd_id::text)        OR
                            (l.category='psu'        AND ma.model_id = l.matched_psu_id::text)        OR
                            (l.category='case'       AND ma.model_id = l.matched_case_id::text)       OR
                            (l.category='lens'       AND ma.model_id = l.matched_lens_id)             OR
                            (l.category='camera'     AND ma.model_id = l.matched_camera_id::text)     OR
                            (l.category='console'    AND ma.model_id = l.matched_console_id::text)    OR
                            (l.category='monitor'    AND ma.model_id = l.monitor_model_id::text)      OR
                            (l.category='motherboard'AND ma.model_id = l.motherboard_model_id::text)
                        )
                    WHERE l.is_active = true AND l.price_eur > 0 {model_filter_sql}
                      AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                )
                SELECT category,
                       ROUND(SUM(GREATEST(upside_eur, 0))::numeric, 2) AS model_upside,
                       ROUND(SUM(GREATEST(haggling_eur, 0))::numeric, 2) AS model_haggling
                FROM per_listing
                GROUP BY category
            """)
            model_upside_by_cat = {}
            model_haggling_by_cat = {}
            for r in cursor.fetchall():
                model_upside_by_cat[r["category"]] = float(r["model_upside"] or 0)
                model_haggling_by_cat[r["category"]] = float(r["model_haggling"] or 0)
            total_model_upside = sum(model_upside_by_cat.values())
            total_model_haggling = sum(model_haggling_by_cat.values())

            # === Top 10 model opportunities: biggest per-model haggling potential
            # (max_ever - min_ever for each individual model). These are the
            # models where there's been the most price volatility historically.
            cursor.execute(f"""
                WITH model_agg AS (
                    SELECT 'gpu' AS category, matched_gpu_id::text AS model_id,
                           MAX(price_eur) AS model_max, MIN(price_eur) AS model_min, COUNT(*) AS n
                    FROM listings WHERE matched_gpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_gpu_id
                    UNION ALL SELECT 'cpu', matched_cpu_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_cpu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_cpu_id
                    UNION ALL SELECT 'ram', matched_ram_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_ram_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ram_id
                    UNION ALL SELECT 'ssd', matched_ssd_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_ssd_id IS NOT NULL AND price_eur > 0 GROUP BY matched_ssd_id
                    UNION ALL SELECT 'psu', matched_psu_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_psu_id IS NOT NULL AND price_eur > 0 GROUP BY matched_psu_id
                    UNION ALL SELECT 'case', matched_case_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_case_id IS NOT NULL AND price_eur > 0 GROUP BY matched_case_id
                    UNION ALL SELECT 'lens', matched_lens_id, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_lens_id IS NOT NULL AND price_eur > 0 GROUP BY matched_lens_id
                    UNION ALL SELECT 'camera', matched_camera_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_camera_id IS NOT NULL AND price_eur > 0 GROUP BY matched_camera_id
                    UNION ALL SELECT 'console', matched_console_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE matched_console_id IS NOT NULL AND price_eur > 0 GROUP BY matched_console_id
                    UNION ALL SELECT 'monitor', monitor_model_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE monitor_model_id IS NOT NULL AND price_eur > 0 GROUP BY monitor_model_id
                    UNION ALL SELECT 'motherboard', motherboard_model_id::text, MAX(price_eur), MIN(price_eur), COUNT(*)
                    FROM listings WHERE motherboard_model_id IS NOT NULL AND price_eur > 0 GROUP BY motherboard_model_id
                )
                SELECT category, model_id, model_max, model_min, n,
                       (model_max - model_min) AS spread
                FROM model_agg
                WHERE n >= 2 AND category IN {cats_in_list}
                ORDER BY spread DESC
                LIMIT 10
            """)
            top_model_opportunities = [
                {
                    "category": r["category"],
                    "model_id": r["model_id"],
                    "model_max": float(r["model_max"]),
                    "model_min": float(r["model_min"]),
                    "n": int(r["n"]),
                    "spread": float(r["spread"]),
                } for r in cursor.fetchall()
            ]

            # === Price health: count of listings with stable / dropping / rising prices
            cursor.execute(f"""
                WITH latest AS (
                    SELECT DISTINCT ON (ph.listing_id)
                        ph.listing_id, ph.price_eur, ph.recorded_at
                    FROM price_history ph
                    ORDER BY ph.listing_id, ph.recorded_at DESC
                ),
                earliest AS (
                    SELECT DISTINCT ON (ph.listing_id)
                        ph.listing_id, ph.price_eur
                    FROM price_history ph
                    ORDER BY ph.listing_id, ph.recorded_at ASC
                )
                SELECT
                    COUNT(*) FILTER (WHERE latest.price_eur = earliest.price_eur) AS stable,
                    COUNT(*) FILTER (WHERE latest.price_eur <  earliest.price_eur) AS dropping,
                    COUNT(*) FILTER (WHERE latest.price_eur >  earliest.price_eur) AS rising
                FROM latest
                JOIN earliest USING (listing_id)
            """)
            ph_row = cursor.fetchone()
            price_health = {
                "stable": int(ph_row["stable"] or 0),
                "dropping": int(ph_row["dropping"] or 0),
                "rising": int(ph_row["rising"] or 0)
            }

            # === Biggest price drops in last 30 days (in €, not % — shows actual bargains) ===
            cursor.execute(f"""
                SELECT
                    l.listing_id, l.title, l.category, l.price_eur AS current_price,
                    l.image_url, l.listing_url,
                    ph.price_eur AS old_price,
                    (ph.price_eur - l.price_eur) AS drop_eur,
                    CASE WHEN ph.price_eur > 0
                         THEN ROUND(((ph.price_eur - l.price_eur) / ph.price_eur * 100)::numeric, 1)
                         ELSE 0 END AS drop_pct
                FROM listings l
                JOIN LATERAL (
                    SELECT MAX(ph.price_eur) AS price_eur
                    FROM price_history ph
                    WHERE ph.listing_id = l.listing_id
                ) ph ON true
                WHERE l.is_active = true
                  AND l.category IN {cats_in_list} {model_filter_sql}
                  AND ph.price_eur > l.price_eur
                  AND l.listing_id NOT IN (SELECT listing_id FROM flagged_listings)
                  AND (
                      l.matched_cpu_id IS NOT NULL OR
                      l.matched_gpu_id IS NOT NULL OR
                      l.matched_ram_id IS NOT NULL OR
                      l.matched_ssd_id IS NOT NULL OR
                      l.matched_psu_id IS NOT NULL OR
                      l.matched_case_id IS NOT NULL OR
                      l.matched_camera_id IS NOT NULL OR
                      l.matched_lens_id IS NOT NULL OR
                      l.matched_console_id IS NOT NULL OR
                      l.monitor_model_id IS NOT NULL OR
                      l.motherboard_model_id IS NOT NULL
                  )
                ORDER BY (ph.price_eur - l.price_eur) DESC
                LIMIT 10
            """)
            recent_drops = []
            for r in cursor.fetchall():
                recent_drops.append({
                    "listing_id": r["listing_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "current_price": float(r["current_price"]),
                    "old_price": float(r["old_price"]),
                    "drop_eur": float(r["drop_eur"]),
                    "drop_pct": float(r.get("drop_pct") or 0),
                    "image_url": r.get("image_url"),
                    "listing_url": r.get("listing_url"),
                    "recorded_at": None,
                })

            # === Lifetime stats: total ever listed, currently delisted, delist rate ===
            # Applies model_filter_sql too so lifetime numbers (and the
            # delist rate) are accurate for the selected model.
            cursor.execute(f"""
                SELECT
                    COUNT(*) AS lifetime_total,
                    COUNT(*) FILTER (WHERE NOT is_active) AS lifetime_delisted,
                    COUNT(*) FILTER (WHERE is_active)  AS currently_active,
                    ROUND((COUNT(*) FILTER (WHERE NOT is_active)::numeric / GREATEST(COUNT(*), 1) * 100), 1) AS delist_rate
                FROM listings l
                WHERE l.category IN {cats_in_list} {model_filter_sql}
            """)
            lifetime = dict(cursor.fetchone())

            # Rollup totals
            total_upside = sum(c["upside_max"] for c in categories)
            total_haggling = total_model_haggling
            total_active_value = sum(c["active_value"] for c in categories)
            biggest_deal = top_deals[0] if top_deals else None
            biggest_drop = top_drops[0] if top_drops else None
            biggest_buy = top_buy_signals[0] if top_buy_signals else None

            # Stitch model stats into categories for the UI
            for c in categories:
                ms = model_stats.get(c["category"], {})
                c["unique_models"] = ms.get("unique_models", 0)
                c["avg_model_max"] = ms.get("avg_model_max", 0)
                c["avg_model_min"] = ms.get("avg_model_min", 0)
                c["haggling_potential"] = ms.get("haggling_potential", 0)
                c["model_upside"] = model_upside_by_cat.get(c["category"], 0)
                c["haggling_max"] = model_haggling_by_cat.get(c["category"], 0)

            return jsonify({
                "totals": {
                    "total_listings": int(totals.get("total_listings") or 0),
                    "active_listings": int(totals.get("active_listings") or 0),
                    "active_value": float(totals.get("active_value") or 0),
                    "avg_price": float(totals.get("avg_price") or 0),
                    "categories_with_listings": int(totals.get("categories_with_listings") or 0),
                    "upside_max": round(total_upside, 2),
                    "model_upside_max": round(total_model_upside, 2),
                    "haggling_max": round(total_haggling, 2),
                    "upside_per_listing": round(total_model_upside / max(int(totals.get("active_listings") or 0), 1), 2),
                    "lifetime_total": int(lifetime.get("lifetime_total") or 0),
                    "lifetime_delisted": int(lifetime.get("lifetime_delisted") or 0),
                    "delist_rate": float(lifetime.get("delist_rate") or 0),
                },
                "categories": categories,
                "selected_categories": selected_cats,
                "selected_model": {
                    "id": model_filter[2]['id'],
                    "category": model_filter[1],
                    "label": _format_model_label(model_filter[1], dict(model_filter[2])),
                } if model_filter else None,
                "match_rates": match_rates,
                "top_deals": top_deals,
                "top_drops": top_drops,
                "top_rises": top_rises,
                "top_buy_signals": top_buy_signals,
                "recent_drops": recent_drops,
                "top_model_opportunities": top_model_opportunities,
                "price_health": price_health,
                "biggest_deal": biggest_deal,
                "biggest_drop": biggest_drop,
                "biggest_buy": biggest_buy,
                "activity_30d": activity,
            })
        except Exception as e:
            cursor.close()
            return jsonify({"error": str(e)}), 500


@app.route('/api/stats')
@cache_control(max_age=30)
def get_stats():
    """Get overall statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        stats = {}

        # GPU stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_gpu_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_gpu_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'gpu'
        """)
        stats['gpu'] = dict(cursor.fetchone())
        print(f"[DEBUG] GPU stats added")

        # CPU stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_cpu_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_cpu_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'cpu'
        """)
        stats['cpu'] = dict(cursor.fetchone())

        # SSD stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_ssd_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_ssd_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'ssd'
        """)
        stats['ssd'] = dict(cursor.fetchone())

        # RAM stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_ram_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_ram_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'ram'
        """)
        stats['ram'] = dict(cursor.fetchone())

        # Lens stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_lens_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_lens_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'lens'
        """)
        stats['lens'] = dict(cursor.fetchone())

        # PSU stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                COUNT(CASE WHEN matched_psu_id IS NOT NULL THEN 1 END) as matched,
                COUNT(CASE WHEN matched_psu_id IS NULL THEN 1 END) as unmatched,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings
            WHERE category = 'psu'
        """)
        stats['psu'] = dict(cursor.fetchone())

        # Recent activity
        cursor.execute("""
            SELECT
                category,
                COUNT(*) as count
            FROM listings
            WHERE first_seen_at > NOW() - INTERVAL '7 days'
            GROUP BY category
        """)
        stats['recent'] = {row['category']: row['count'] for row in cursor.fetchall()}

        cursor.close()

        return jsonify(stats)


@app.route('/api/price-trends')
@cache_control(max_age=30)
def get_price_trends():
    """Return daily average price trends per category for the dashboard chart."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            time_filter = request.args.get('time', 'month')
            category_filter = request.args.get('category', 'all')

            if time_filter == 'week':
                interval = "7 days"
            elif time_filter == 'month':
                interval = "30 days"
            elif time_filter == 'year':
                interval = "1 year"
            else:
                interval = None

            categories = ['gpu', 'cpu', 'ssd', 'ram', 'psu', 'case']
            if category_filter and category_filter != 'all' and category_filter in categories:
                categories = [category_filter]

            params = []
            date_filter = ""
            if interval:
                date_filter = "AND ph.recorded_at > NOW() - INTERVAL %s"
                params.append(interval)

            cursor.execute(f"""
                SELECT
                    l.category,
                    DATE(ph.recorded_at) as date,
                    ROUND(AVG(ph.price_eur)::numeric, 2) as avg_price,
                    COUNT(*) as sample_count
                FROM price_history ph
                JOIN listings l ON ph.listing_id = l.listing_id
                WHERE l.category = ANY(%s)
                  AND ph.price_eur IS NOT NULL
                  {date_filter}
                GROUP BY l.category, DATE(ph.recorded_at)
                ORDER BY l.category, date
            """, (categories, *params))
            rows = [dict(row) for row in cursor.fetchall()]

            # Build labels (union of all dates)
            labels = sorted({row['date'].isoformat() if row.get('date') else None for row in rows})
            labels = [d for d in labels if d]

            # Build datasets per category
            datasets = []
            trend_info = {}
            for category in categories:
                cat_rows = [r for r in rows if r.get('category') == category]
                price_by_date = {r['date'].isoformat(): float(r['avg_price']) for r in cat_rows if r.get('date')}
                data = [price_by_date.get(d) for d in labels]
                if not any(v is not None for v in data):
                    continue
                datasets.append({
                    'label': category.upper(),
                    'data': data,
                    'category': category
                })
                # trend from first to last non-null point
                non_null = [(d, price_by_date[d]) for d in labels if d in price_by_date]
                if len(non_null) >= 2:
                    first_price = non_null[0][1]
                    last_price = non_null[-1][1]
                    change = last_price - first_price
                    trend_info[category] = {
                        'direction': 'up' if change > 0 else ('down' if change < 0 else 'flat'),
                        'percentage': (change / first_price * 100) if first_price else 0.0,
                        'change': round(change, 2)
                    }

            cursor.close()

            return jsonify({
                'labels': labels,
                'datasets': datasets,
                'trend_info': trend_info
            })
        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/gpus')
@cache_control(max_age=30)
def get_gpus():
    """Get GPU listings with filters and sorting."""
    cursor = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get query parameters
            show_active = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('min_confidence', 0))
            time_filter = request.args.get('time', 'all_time')  # week, month, all_time
            sort_by = request.args.get('sort', 'date_posted')  # price, date_posted
            sort_order = request.args.get('order', 'desc')  # asc, desc

            # NEW: GPU-specific filter parameters
            vendor_filter = request.args.get('vendor', '')
            model_filter = request.args.get('model', '')
            vram_filter = request.args.get('vram', '')
            strict_match = request.args.get('strict_match', 'false').lower() == 'true'
            source_filter = request.args.get('source', '')
            price_min = request.args.get('price_min', '')
            price_max = request.args.get('price_max', '')
            unicorn_filter = request.args.get('unicorn', '')
            price_drop = request.args.get('price_drop', '').lower() == 'true'

            use_active_avg = request.args.get('use_active_avg', 'false').lower() == 'true'
            rank_min = request.args.get('rank_min', '')
            rank_max = request.args.get('rank_max', '')
            limit = request.args.get('limit', '100')
            try:
                limit = max(1, min(10000, int(limit)))
            except ValueError:
                limit = 100

            params = []
            where_clauses = ["l.category = 'gpu'"]

            if show_active:
                where_clauses.append("l.is_active = true")
            # _unmatched_filter_sql() returns a fragment like " AND x IS NOT NULL ".
            # We're using a list joined with " AND " — strip the leading "AND "
            # so the joiner doesn't produce a double-AND SQL error.
            _unmatched = _unmatched_filter_sql('gpu').strip()
            if _unmatched.upper().startswith('AND '):
                _unmatched = _unmatched[4:]
            if _unmatched:
                where_clauses.append(_unmatched)
            if min_confidence > 0:
                where_clauses.append("l.confidence_score >= %s")
                params.append(min_confidence)

            # NEW: Add price range filter
            if price_min:
                where_clauses.append("l.price_eur >= %s")
                params.append(float(price_min))
            if price_max:
                where_clauses.append("l.price_eur <= %s")
                params.append(float(price_max))

            # NEW: Add G3D rank range filter (lower rank = better GPU)
            if rank_min:
                where_clauses.append("COALESCE(gs.g3d_rank, 999999) >= %s")
                params.append(int(rank_min))
            if rank_max:
                where_clauses.append("COALESCE(gs.g3d_rank, 999999) <= %s")
                params.append(int(rank_max))

            # NEW: Add vendor filter (exclude 'all')
            if vendor_filter and vendor_filter.lower() != 'all':
                where_clauses.append("g.vendor ILIKE %s")
                params.append(f'%{vendor_filter}%')

            # NEW: Add model filter (exclude 'all') - use LIKE to match base model names (e.g., "GeForce GTX 1060" matches "GeForce GTX 1060 6GB")
            if model_filter and model_filter.lower() != 'all':
                if strict_match:
                    # Match models that start with the selected base name but exclude Ti/Super/XT variants
                    where_clauses.append("g.model ILIKE %s")
                    params.append(f'{model_filter}%')
                    where_clauses.append("g.model !~* %s")
                    params.append(f'^{re.escape(model_filter)}\\s+(Ti|Super|XT).*')
                else:
                    # Match models that start with the base name (handles "GeForce GTX 1060" matching "GeForce GTX 1060 6GB" and "GeForce GTX 1060 3GB")
                    where_clauses.append("g.model ILIKE %s")
                    params.append(f'{model_filter}%')

            # NEW: Add VRAM filter with optional exact/min mode
            if vram_filter:
                try:
                    # The vram_gb column stores VRAM in MB, but the frontend presents it in GB.
                    # The value sent by the frontend is the raw MB value, so use it directly.
                    vram_mb = int(vram_filter)
                    vram_mode = request.args.get('vram_mode', 'exact').lower()
                    if vram_mode == 'min':
                        where_clauses.append("g.vram_gb >= %s")
                    else:
                        where_clauses.append("g.vram_gb = %s")
                    params.append(vram_mb)
                except ValueError:
                    pass  # Ignore invalid vram values

            # DEBUG: Log VRAM filter parameters explicitly

            # NEW: Add source filter
            if source_filter and source_filter.lower() != 'all':
                where_clauses.append("l.source = %s")
                params.append(source_filter)

            # Exclude flagged listings (unless viewing flagged specifically)
            if request.args.get('include_flagged', '').lower() != 'true':
                where_clauses.append("NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)")

            # Build the query
            query = f"""
                WITH best_passmark AS (
                    SELECT DISTINCT ON (gpu_reference_id)
                        gpu_reference_id,
                        g3d_mark,
                        g2d_mark
                    FROM gpu_reference_passmark
                    WHERE g3d_mark IS NOT NULL
                    ORDER BY gpu_reference_id, g3d_mark DESC
                ),
                gpu_scores AS (
                    SELECT
                        gpu_reference_id,
                        g3d_mark,
                        g2d_mark,
                        RANK() OVER (ORDER BY g3d_mark DESC) as g3d_rank,
                        COUNT(*) OVER () as total_ranked
                    FROM best_passmark
                ),
                gpu_versioned AS (
                    SELECT
                        listing_id,
                        CASE WHEN listing_id ~ '_v\\d+$' THEN regexp_replace(listing_id, '_v\\d+$', '') ELSE listing_id END as base_id,
                        CASE WHEN listing_id ~ '_v(\\d+)$' THEN (regexp_match(listing_id, '_v(\\d+)$'))[1]::int ELSE 0 END as version_num
                    FROM listings
                    WHERE category = 'gpu'
                ),
                latest_gpu_version AS (
                    SELECT base_id, MAX(version_num) as max_version
                    FROM gpu_versioned
                    GROUP BY base_id
                )
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.confidence_score,
                    l.match_method,
                    l.matched_gpu_id,
                    l.source,
                    l.local_image_path,
                    g.vendor,
                    g.model as gpu_model,
                    g.vram_gb,
                    g.year_released,
                    g.msrp_usd,
                    l.image_url,
                    l.listing_url,
                    gs.g3d_mark,
                    gs.g2d_mark,
                    gs.g3d_rank,
                    gs.total_ranked
                FROM listings l
                LEFT JOIN gpu_reference g ON l.matched_gpu_id = g.id
                LEFT JOIN gpu_scores gs ON g.id = gs.gpu_reference_id
                JOIN gpu_versioned gv ON l.listing_id = gv.listing_id
                JOIN latest_gpu_version lgv ON gv.base_id = lgv.base_id AND gv.version_num = lgv.max_version
                WHERE {' AND '.join(where_clauses)}
            """

            # Add time filter
            query += get_time_filter_sql(time_filter)

            # Add sorting
            if sort_by == 'price':
                sort_column = 'l.price_eur'
            elif sort_by == 'performance_price':
                sort_column = 'COALESCE(gs.g3d_mark, 0) / NULLIF(l.price_eur, 0)'
            elif sort_by == 'rank':
                sort_column = 'COALESCE(gs.g3d_rank, 999999)'
            else:
                sort_column = 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT %s"
            params.append(limit)

            try:
                cursor.execute(query, params)
                listings = cursor.fetchall()

                # Pre-load latest price history entries for returned listings
                listing_ids = [l['listing_id'] for l in listings]
                price_map = get_price_changes_for_listings(cursor, listing_ids)

                # Add price statistics for each GPU model (active-only or all listings)
                gpu_stats = {}
                active_stats_clause, flagged_clause = get_active_avg_clauses(request)
                cursor.execute(f"""
                    WITH gpu_versioned AS (
                        SELECT
                            listing_id,
                            CASE WHEN listing_id ~ '_v\\d+$' THEN regexp_replace(listing_id, '_v\\d+$', '') ELSE listing_id END as base_id,
                            CASE WHEN listing_id ~ '_v(\\d+)$' THEN (regexp_match(listing_id, '_v(\\d+)$'))[1]::int ELSE 0 END as version_num
                        FROM listings
                        WHERE category = 'gpu'
                    ),
                    latest_gpu_version AS (
                        SELECT base_id, MAX(version_num) as max_version
                        FROM gpu_versioned
                        GROUP BY base_id
                    )
                    SELECT
                        g.id,
                        g.vendor,
                        g.model,
                        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM listings l
                    JOIN gpu_versioned gv ON l.listing_id = gv.listing_id
                    JOIN latest_gpu_version lgv ON gv.base_id = lgv.base_id AND gv.version_num = lgv.max_version
                    JOIN gpu_reference g ON l.matched_gpu_id = g.id
                    WHERE l.category = 'gpu'
                        {active_stats_clause}
                        {flagged_clause}
                    GROUP BY g.id, g.vendor, g.model
                """, tuple())
                for row in cursor.fetchall():
                    gpu_stats[row['id']] = dict(row)

                # Enhance listings with price comparison and format VRAM
                enhanced_listings = []

                for listing in listings:
                    listing_dict = dict(listing)
                    # Format VRAM from MB to GB
                    if listing_dict.get('vram_gb'):
                        listing_dict['vram_gb'] = format_vram(listing_dict['vram_gb'])

                    # Hide Andele location, show X instead
                    if listing_dict.get('seller_location', '').lower() == 'andele':
                        listing_dict['seller_location'] = 'X'

                    if listing_dict.get('matched_gpu_id') and listing_dict['matched_gpu_id'] in gpu_stats:
                        stats = gpu_stats[listing_dict['matched_gpu_id']]
                        listing_dict['price_stats'] = {
                            'avg': stats['avg_price'],
                            'min': stats['min_price'],
                            'max': stats['max_price'],
                            'below_avg': listing_dict['price_eur'] < stats['avg_price'],
                            'percentile': round((listing_dict['price_eur'] - stats['min_price']) /
                                              (stats['max_price'] - stats['min_price']) * 100, 1)
                                              if stats['max_price'] > stats['min_price'] else 50,
                            'listing_count': stats['listing_count']  # Add count for unicorn detection
                        }
                        # Mark as unicorn if only 1 listing exists for this model
                        if stats['listing_count'] == 1:
                            listing_dict['is_unicorn'] = True

                    # Detect price decreases from price history
                    listing_dict['has_price_decreased'] = False
                    listing_dict['price_changes'] = []
                    detect_price_decrease(listing_dict, price_map.get(listing_dict['listing_id']))
                    if price_drop and not listing_dict.get('has_price_decreased'):
                        continue

                    # Mark as new if this listing is from the latest import for GPU category
                    listing_dict['is_new'] = is_listing_new(listing_dict.get('first_seen_at'), 'gpu')

                    # Format g3d_rank as percentile tier if available
                    if listing_dict.get('g3d_rank') and listing_dict.get('total_ranked'):
                        total = listing_dict['total_ranked']
                        rank = listing_dict['g3d_rank']
                        if total > 0:
                            listing_dict['performance_tier'] = f"Top {round((rank / total) * 100, 1)}%"

                    if listing_dict['is_new']:
                        listing_dict['new_badge_reason'] = 'first_seen_today'
                    enhanced_listings.append(listing_dict)

                # Apply unicorn filter (only/exclude)
                if unicorn_filter == 'only':
                    enhanced_listings = [l for l in enhanced_listings if l.get('is_unicorn')]
                elif unicorn_filter == 'exclude':
                    enhanced_listings = [l for l in enhanced_listings if not l.get('is_unicorn')]

                cursor.close()

                return jsonify(enhanced_listings)

            except Exception as e:
                import traceback
                traceback.print_exc()
                if cursor:
                    cursor.close()
                # Always return an array to prevent frontend .map() errors
                return jsonify([]), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Always return an array to prevent frontend .map() errors
        return jsonify([]), 500



@app.route('/api/gpu-performance-stats')
@cache_control(max_age=30)
def get_gpu_performance_stats():
    """Return GPU performance/price scatter and vendor averages for charts."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                WITH best_passmark AS (
                    SELECT DISTINCT ON (gpu_reference_id)
                        gpu_reference_id,
                        g3d_mark,
                        g2d_mark
                    FROM gpu_reference_passmark
                    WHERE g3d_mark IS NOT NULL
                    ORDER BY gpu_reference_id, g3d_mark DESC
                ),
                gpu_price_stats AS (
                    SELECT
                        g.id,
                        g.vendor,
                        g.model,
                        g.vram_gb,
                        AVG(l.price_eur) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM listings l
                    JOIN gpu_reference g ON l.matched_gpu_id = g.id
                    WHERE l.category = 'gpu'
                        AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                    GROUP BY g.id, g.vendor, g.model, g.vram_gb
                )
                SELECT
                    p.gpu_reference_id,
                    g.vendor,
                    g.model,
                    g.vram_gb,
                    p.g3d_mark,
                    p.g2d_mark,
                    s.avg_price,
                    s.min_price,
                    s.max_price,
                    s.listing_count,
                    CASE WHEN p.g3d_mark > 0 AND s.avg_price > 0
                         THEN ROUND((s.avg_price / p.g3d_mark)::numeric, 4)
                         ELSE NULL
                    END as price_per_g3d
                FROM best_passmark p
                JOIN gpu_reference g ON p.gpu_reference_id = g.id
                LEFT JOIN gpu_price_stats s ON g.id = s.id
                WHERE s.avg_price IS NOT NULL
                ORDER BY p.g3d_mark DESC
                LIMIT 10
            """)
            scatter = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                WITH best_passmark AS (
                    SELECT DISTINCT ON (gpu_reference_id)
                        gpu_reference_id,
                        g3d_mark
                    FROM gpu_reference_passmark
                    WHERE g3d_mark IS NOT NULL
                    ORDER BY gpu_reference_id, g3d_mark DESC
                )
                SELECT g.vendor, ROUND(AVG(p.g3d_mark)::numeric, 0) as avg_g3d, COUNT(*) as gpu_count
                FROM best_passmark p
                JOIN gpu_reference g ON p.gpu_reference_id = g.id
                GROUP BY g.vendor
                ORDER BY avg_g3d DESC
            """)
            vendor_avg = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                WITH best_passmark AS (
                    SELECT DISTINCT ON (gpu_reference_id)
                        gpu_reference_id,
                        g3d_mark
                    FROM gpu_reference_passmark
                    WHERE g3d_mark IS NOT NULL
                    ORDER BY gpu_reference_id, g3d_mark DESC
                ),
                gpu_value AS (
                    SELECT
                        g.id,
                        g.vendor,
                        g.model,
                        p.g3d_mark,
                        AVG(l.price_eur) as avg_price,
                        CASE WHEN p.g3d_mark > 0 AND AVG(l.price_eur) > 0
                             THEN AVG(l.price_eur) / p.g3d_mark
                             ELSE NULL
                        END as price_per_g3d
                    FROM listings l
                    JOIN gpu_reference g ON l.matched_gpu_id = g.id
                    JOIN best_passmark p ON g.id = p.gpu_reference_id
                    WHERE l.category = 'gpu'
                        AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                    GROUP BY g.id, g.vendor, g.model, p.g3d_mark
                )
                SELECT
                    CASE
                        WHEN price_per_g3d < 0.05 THEN '0.00-0.05 €/pt'
                        WHEN price_per_g3d < 0.10 THEN '0.05-0.10 €/pt'
                        WHEN price_per_g3d < 0.20 THEN '0.10-0.20 €/pt'
                        WHEN price_per_g3d < 0.50 THEN '0.20-0.50 €/pt'
                        WHEN price_per_g3d < 1.00 THEN '0.50-1.00 €/pt'
                        ELSE '>1.00 €/pt'
                    END as bucket,
                    COUNT(*) as gpu_count
                FROM gpu_value
                WHERE price_per_g3d IS NOT NULL
                GROUP BY 1
                ORDER BY MIN(price_per_g3d)
            """)
            value_buckets = [dict(row) for row in cursor.fetchall()]

            cursor.close()

            # Best-value dataset: lowest € per G3D point among matched models
            value_per_point = []
            for row in sorted(scatter, key=lambda r: r['price_per_g3d'] or float('inf')):
                if row.get('price_per_g3d') and row.get('g3d_mark'):
                    value_per_point.append({
                        'x': float(row['g3d_mark']),
                        'y': float(row['price_per_g3d']),
                        'label': f"{row['vendor']} {row['model']}",
                        'vram': format_vram(row.get('vram_gb')),
                        'avg_price': float(row['avg_price']) if row.get('avg_price') else None
                    })
            value_per_point = value_per_point[:10]

            return jsonify({
                'scatter': scatter,
                'vendor_avg_g3d': vendor_avg,
                'value_buckets': value_buckets,
                'value_per_point': value_per_point
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'scatter': [], 'vendor_avg_g3d': [], 'value_buckets': []}), 500


@app.route('/api/cpus')
@cache_control(max_age=30)
def get_cpus():
    """Get CPU listings with filters."""
    cursor = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            show_active = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('min_confidence', 0))
            time_filter = request.args.get('time', 'all_time')
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            cpu_type_filter = request.args.get('cpu_type', '')
            cpu_class_filter = request.args.get('cpu_class', '')
            source_filter = request.args.get('source', '')
            vendor_filter = request.args.get('vendor', '')
            series_filter = request.args.get('series', '')
            try:
                limit = int(request.args.get('limit', 100))
                if limit < 1 or limit > 10000:
                    limit = 100
            except ValueError:
                limit = 100

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.created_at,
                    l.is_active,
                    l.cpu_confidence_score as confidence_score,
                    l.cpu_match_method as match_method,
                    l.matched_cpu_id,
                    c.producer as vendor,
                    c.cpu_name,
                    c.processor_number,
                    c.cores,
                    c.threads,
                    c.socket,
                    c.base_freq,
                    COALESCE(agg.cinebench_r23_multi, r23.cinebench_r23_multi) AS cinebench_r23_multi,
                    COALESCE(agg.cinebench_r26_multi, r26.cinebench_r26_multi) AS cinebench_r26_multi,
                    COALESCE(agg.passmark_score, pm.passmark_score) AS passmark_cpu_mark,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url
                FROM listings l
                LEFT JOIN cpu_reference c ON l.matched_cpu_id = c.id
                LEFT JOIN cpu_complete_data agg ON c.id = agg.cpu_reference_id
                LEFT JOIN cpu_benchmarks_r23 r23 ON c.cpu_name = r23.cpu_name
                LEFT JOIN cpu_benchmarks_r26 r26 ON c.cpu_name = r26.cpu_name
                LEFT JOIN cpu_benchmarks_passmark pm ON c.cpu_name = pm.cpu_name
                WHERE l.category = 'cpu'
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('cpu')
            if min_confidence > 0:
                query += " AND l.cpu_confidence_score >= %s"
                params.append(min_confidence)

            if cpu_type_filter:
                query += " AND c.producer ILIKE %s"
                params.append(f'%{cpu_type_filter}%')

            # Add vendor filter
            if vendor_filter and vendor_filter.lower() != 'all':
                query += " AND c.producer ILIKE %s"
                params.append(f'%{vendor_filter}%')

            # Add series filter (i3, i5, i7, Ryzen 5, etc)
            if series_filter:
                query += " AND c.processor_number ILIKE %s"
                params.append(f'%{series_filter}%')

            # Add model filter. Exact match (ILIKE without wildcards) so
            # picking "Intel Core i7-6700" doesn't also pull in i7-6700K /
            # i7-6700T / i7-6700HQ / i7-6700TE, which are separate models.
            model_filter = request.args.get('model', '')
            if model_filter:
                query += " AND (c.cpu_name ILIKE %s OR c.processor_number ILIKE %s)"
                params.append(model_filter)
                params.append(model_filter)

            # Add source filter
            if source_filter and source_filter.lower() != 'all':
                query += " AND l.source = %s"
                params.append(source_filter)

            # Apply CPU class filter in SQL when possible to reduce payload.
            # This only works when the row references cpu_reference. Listings with
            # NULL matched_cpu_id or cpu_name/processor_number cannot match a real
            # class and will be excluded by an exact filter.
            if cpu_class_filter:
                # Build the SQL condition that mirrors get_cpu_class() family
                # tokens, but with simple ILIKE checks.
                family_tokens = {
                    'Budget': ["i3", "pentium", "celeron", "core2", "core duo", "ryzen 3", "athlon", "a-series", "phenom"],
                    'Mid-Range': ["i5", "fx", "ryzen 5"],
                    'High-End': ["i7", "ryzen 7"],
                    'Enthusiast': ["i9", "xeon", "ryzen 9", "threadripper"],
                }
                if cpu_class_filter in family_tokens:
                    conditions = []
                    for token in family_tokens[cpu_class_filter]:
                        conditions.append("(c.processor_number ILIKE %s OR c.cpu_name ILIKE %s)")
                        like = f'%{token}%'
                        params.append(like)
                        params.append(like)
                    query += " AND (" + " OR ".join(conditions) + ")"

            query += get_time_filter_sql(time_filter)

            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            # Map frontend sort options to SQL expressions. Price/perf metrics are
            # computed in SQL so sorting works server-side before LIMIT 100.
            if sort_by == 'price':
                sort_expr = 'l.price_eur'
            elif sort_by == 'r23_score':
                sort_expr = 'COALESCE(agg.cinebench_r23_multi, r23.cinebench_r23_multi)'
            elif sort_by == 'passmark_score':
                sort_expr = 'COALESCE(agg.passmark_score, pm.passmark_score)'
            elif sort_by == 'price_per_r23':
                sort_expr = 'l.price_eur / NULLIF(COALESCE(agg.cinebench_r23_multi, r23.cinebench_r23_multi), 0) * 1000'
            elif sort_by == 'price_per_passmark':
                sort_expr = 'l.price_eur / NULLIF(COALESCE(agg.passmark_score, pm.passmark_score), 0) * 1000'
            else:
                sort_expr = 'l.date_posted'
            query += f" ORDER BY {sort_expr} {sort_dir} NULLS LAST LIMIT {limit}"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Add price statistics for each CPU model
            cpu_stats = {}
            cursor.execute("""
                SELECT
                    c.id,
                    c.cpu_name,
                    c.processor_number,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(*) as listing_count
                FROM listings l
                JOIN cpu_reference c ON l.matched_cpu_id = c.id
                WHERE l.category = 'cpu' AND l.is_active = true
                GROUP BY c.id, c.cpu_name, c.processor_number
            """)
            for row in cursor.fetchall():
                cpu_stats[row['id']] = dict(row)

            # Enhance listings with price comparison
            enhanced_listings = []
            for listing in listings:
                listing_dict = dict(listing)
                if listing['matched_cpu_id'] and listing['matched_cpu_id'] in cpu_stats:
                    stats = cpu_stats[listing['matched_cpu_id']]
                    listing_dict['price_stats'] = {
                        'avg': stats['avg_price'],
                        'min': stats['min_price'],
                        'max': stats['max_price'],
                        'below_avg': listing['price_eur'] < stats['avg_price'],
                        'percentile': round((listing['price_eur'] - stats['min_price']) /
                                          (stats['max_price'] - stats['min_price']) * 100, 1)
                                          if stats['max_price'] > stats['min_price'] else 50,
                        'listing_count': stats['listing_count']
                    }
                    # Mark as unicorn if only 1 listing exists for this CPU model
                    if stats['listing_count'] == 1:
                        listing_dict['is_unicorn'] = True

                # Mark as new if this listing is from the latest import for CPU category
                listing_dict['is_new'] = is_listing_new(listing_dict.get('first_seen_at'), 'cpu')

                # Build benchmarks object for frontend table columns
                benchmarks = {}
                r23 = listing_dict.get('cinebench_r23_multi')
                r26 = listing_dict.get('cinebench_r26_multi')
                passmark = listing_dict.get('passmark_cpu_mark')
                if r23:
                    benchmarks['r23_multi'] = r23
                if r26:
                    benchmarks['r26_multi'] = r26
                if passmark:
                    benchmarks['passmark'] = passmark
                if benchmarks:
                    listing_dict['benchmarks'] = benchmarks

                # Calculate price/performance metrics
                price = float(listing_dict.get('price_eur', 0))
                if price > 0:
                    if r23:
                        listing_dict['price_per_r23'] = round(price / (r23 / 1000), 2)
                    if passmark:
                        listing_dict['price_per_passmark'] = round(price / (passmark / 1000), 2)

                # Derive CPU performance class for frontend chart/filter
                listing_dict['cpu_class'] = get_cpu_class(listing_dict)

                # Apply CPU class filter post-query if requested
                if cpu_class_filter and listing_dict['cpu_class'] != cpu_class_filter:
                    continue

                enhanced_listings.append(listing_dict)

            cursor.close()

            return jsonify(enhanced_listings)
    except Exception as e:
        import traceback
        traceback.print_exc()
        if cursor:
            cursor.close()
        # Always return an array to prevent frontend .forEach() errors
        return jsonify([]), 500


@app.route('/api/price-history/<listing_id>')
@cache_control(max_age=30)
def get_price_history(listing_id):
    """Get price history for a specific listing, including prior versions."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Compute base id so versioned listings include their ancestors' history
        base_id = re.sub(r'_v\d+$', '', listing_id)
        if base_id == listing_id:
            cursor.execute("""
                SELECT price_eur, recorded_at
                FROM price_history
                WHERE listing_id = %s
                ORDER BY recorded_at ASC
            """, (listing_id,))
        else:
            # Include all versions of the same base listing
            cursor.execute("""
                SELECT price_eur, recorded_at
                FROM price_history
                WHERE listing_id ~ %s
                ORDER BY recorded_at ASC
            """, (f'^{re.escape(base_id)}(_v\\d+)?$',))

        history = cursor.fetchall()

        cursor.close()

        return jsonify([convert_decimal_to_float(dict(row)) for row in history])


@app.route('/api/listing-details/<listing_id>')
@cache_control(max_age=30)
def get_listing_details(listing_id):
    """Get detailed information for a specific listing including price history."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get the current listing with CPU/GPU/Case/Console details based on its category.
        cursor.execute("""
            SELECT
                l.listing_id,
                l.title,
                l.price_eur,
                l.description,
                l.source,
                l.image_url,
                l.local_image_path,
                l.category,
                l.matched_gpu_id,
                g.model as gpu_model,
                l.matched_cpu_id,
                c.producer as vendor,
                c.cpu_name,
                c.processor_number,
                c.cores,
                c.threads,
                c.socket,
                l.matched_case_id,
                cr.name as case_name,
                cr.type as case_type,
                cr.color as case_color,
                l.case_confidence_score,
                l.case_match_method,
                l.matched_console_id,
                con.name as console_name,
                con.company as console_company,
                con.generation as console_generation,
                l.date_posted,
                l.listing_url,
                l.seller_location,
                l.is_active
            FROM listings l
            LEFT JOIN gpu_reference g ON l.matched_gpu_id = g.id
            LEFT JOIN cpu_reference c ON l.matched_cpu_id = c.id
            LEFT JOIN case_reference cr ON l.matched_case_id = cr.id
            LEFT JOIN console_reference con ON l.matched_console_id::integer = con.id
            WHERE l.listing_id = %s
        """, (listing_id,))

        current = cursor.fetchone()

        # Fallback for category-specific tables (e.g. console_listings) not in main listings table.
        if not current:
            cursor.execute("""
                SELECT
                    cl.listing_id,
                    cl.title,
                    cl.price_eur,
                    cl.title as description,
                    'ss.lv' as source,
                    cl.image_url,
                    NULL as local_image_path,
                    'console' as category,
                    NULL as matched_gpu_id,
                    NULL as gpu_model,
                    NULL as matched_cpu_id,
                    NULL as vendor,
                    NULL as cpu_name,
                    NULL as processor_number,
                    NULL as cores,
                    NULL as threads,
                    NULL as socket,
                    NULL as matched_case_id,
                    NULL as case_name,
                    NULL as case_type,
                    NULL as case_color,
                    cl.matched_console_id,
                    cr.name as console_name,
                    cr.company as console_company,
                    cr.generation as console_generation,
                    cv.model_name as variant_name,
                    ce.edition_name,
                    cl.is_special_edition,
                    cl.date_posted,
                    cl.listing_url,
                    cl.seller_location,
                    cl.is_active
                FROM console_listings cl
                LEFT JOIN console_reference cr ON cl.matched_console_id = cr.id
                LEFT JOIN console_variants cv ON cl.matched_variant_id = cv.id
                LEFT JOIN console_editions ce ON cl.matched_edition_id = ce.id
                WHERE cl.listing_id = %s
            """, (listing_id,))
            current = cursor.fetchone()

        # Fallback for laptop-specific table.
        if not current:
            cursor.execute("""
                SELECT
                    ll.listing_id,
                    ll.title,
                    ll.price_eur,
                    ll.description,
                    'ss.lv' as source,
                    ll.image_url,
                    ll.local_image_path,
                    'laptop' as category,
                    ll.date_posted,
                    ll.listing_url,
                    ll.seller_location,
                    ll.is_active,
                    ll.brand,
                    ll.model,
                    ll.display_size,
                    ll.cpu_raw,
                    ll.cpu_freq_ghz,
                    ll.ram_gb,
                    ll.storage_gb,
                    ll.storage_type,
                    ll.gpu_raw,
                    ll.seller_type,
                    ll.condition_state,
                    lr.id AS laptop_ref_id,
                    lr.brand AS laptop_brand,
                    lr.model AS laptop_model,
                    lr.model_number AS laptop_model_number,
                    lr.material,
                    lr.usb_c_count,
                    lr.usb_count,
                    lr.hdmi_count,
                    lr.has_hdmi,
                    lr.has_video_pd_usb_c,
                    lr.has_ethernet,
                    lr.has_touchscreen,
                    lr.refresh_rate_hz,
                    lr.resolution AS laptop_resolution,
                    lr.is_valid AS laptop_ref_valid,
                    lrc.id AS cpu_ref_id,
                    lrc.brand AS cpu_brand_normalized,
                    lrc.model AS cpu_model_normalized
                FROM laptop_listings ll
                LEFT JOIN laptop_reference lr ON lr.id = ll.laptop_reference_id
                LEFT JOIN laptop_reference_cpu lrc ON lrc.id = ll.cpu_reference_id
                WHERE ll.listing_id = %s
            """, (listing_id,))
            current = cursor.fetchone()

        if not current:
            cursor.close()
            return jsonify({'error': 'Listing not found'}), 404

        # Get price history for this listing, including prior versions for versioned IDs
        base_id = re.sub(r'_v\d+$', '', listing_id)
        if base_id == listing_id:
            # Use laptop_price_history for laptop listings, generic price_history otherwise
            history_table = 'laptop_price_history' if current.get('category') == 'laptop' else 'price_history'
            cursor.execute("""
                SELECT price_eur, recorded_at, change_type
                FROM """ + history_table + """
                WHERE listing_id = %s
                ORDER BY recorded_at DESC
            """, (listing_id,))
        else:
            cursor.execute("""
                SELECT price_eur, recorded_at, change_type
                FROM price_history
                WHERE listing_id ~ %s
                ORDER BY recorded_at DESC
            """, (f'^{re.escape(base_id)}(_v\\d+)?$',))

        history = cursor.fetchall()

        # Compute summary stats across the full price history (including
        # the current listing price if no history rows exist). Returned as
        # `current.price_stats` so the popup's "Lowest ever / Avg ever /
        # Highest ever" cards can render without a second round-trip.
        all_prices = [float(h['price_eur']) for h in history if h.get('price_eur') is not None]
        if current.get('price_eur') is not None and float(current['price_eur']) > 0:
            all_prices.append(float(current['price_eur']))
        price_stats = None
        if all_prices:
            current_dict = convert_decimal_to_float(dict(current))
            price_stats = {
                'min': min(all_prices),
                'max': max(all_prices),
                'avg': sum(all_prices) / len(all_prices),
                'count': len(history),
                'min_count': sum(1 for h in history if h.get('price_eur') is not None and float(h['price_eur']) == min(all_prices)),
                'avg_count': len(history),
            }
            current_dict['price_stats'] = price_stats
        else:
            current_dict = convert_decimal_to_float(dict(current))

        cursor.close()

        return jsonify({
            'current': current_dict,
            'history': [convert_decimal_to_float(dict(row)) for row in history]
        })


@app.route('/api/model-history/<model_type>/<int:model_id>')
@cache_control(max_age=30)
def get_model_history(model_type, model_id):
    """Get all historical prices for a specific model."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if model_type == 'gpu':
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.listing_url,
                    l.local_image_path,
                    l.image_url
                FROM listings l
                WHERE l.matched_gpu_id = %s AND l.category = 'gpu'
                ORDER BY l.date_posted DESC
            """, (model_id,))
        elif model_type == 'ssd':
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.listing_url,
                    l.local_image_path,
                    l.image_url
                FROM listings l
                WHERE l.matched_ssd_id = %s AND l.category = 'ssd'
                ORDER BY l.date_posted DESC
            """, (model_id,))
        else:
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.listing_url,
                    l.local_image_path,
                    l.image_url
                FROM listings l
                WHERE l.matched_cpu_id = %s AND l.category = 'cpu'
                ORDER BY l.date_posted DESC
            """, (model_id,))

        listings = cursor.fetchall()

        # Calculate stats for the model
        prices = [float(row['price_eur']) for row in listings if row['price_eur']]
        stats = {}
        if prices:
            stats = {
                'avg': round(sum(prices) / len(prices), 2),
                'min': round(min(prices), 2),
                'max': round(max(prices), 2),
                'count': len(prices)
            }

        # Fetch model info for CPU reference
        model_info = {}
        if model_type == 'cpu':
            try:
                cursor.execute("""
                    SELECT id, cpu_name, producer, cores, threads, base_freq
                    FROM cpu_reference
                    WHERE id = %s
                """, (model_id,))
                row = cursor.fetchone()
                if row:
                    model_info = dict(row)
            except Exception:
                pass

        cursor.close()

        return jsonify({
            'listings': [convert_decimal_to_float(dict(row)) for row in listings],
            'stats': stats,
            'model_info': model_info
        })


@app.route('/api/gpu-models/<int:gpu_id>')
@cache_control(max_age=600)
def get_gpu_model_by_id(gpu_id: int):
    """Look up a single GPU model by id. Used by the GPU flag
    'wrong model' correction UI to confirm the typed ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT id, vendor, model, raw_model, vram_gb, memory_type,
                       year_released, msrp_usd, search_keywords, normalized_name
                FROM gpu_reference WHERE id = %s
            """, (gpu_id,))
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return jsonify({'error': 'GPU not found'}), 404
            return jsonify(convert_decimal_to_float(dict(row)))
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return jsonify({'error': str(e)}), 500


@app.route('/api/gpu-models')
@cache_control(max_age=30)
def get_gpu_models():
    """Get aggregated GPU model statistics with sorting."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        sort = request.args.get('sort', 'price_desc')
        time_filter = request.args.get('time', 'all_time')

        order_map = {
            'price_desc': 'avg_price DESC',
            'price_asc': 'avg_price ASC',
            'listings_desc': 'active_listings DESC',
            'listings_asc': 'active_listings ASC'
        }
        order_by = order_map.get(sort, 'avg_price DESC')

        date_clause = get_time_filter_sql(time_filter, 'l')
        active_time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

        cursor.execute(f"""
            SELECT
                g.id,
                g.vendor,
                g.model,
                g.vram_gb,
                g.year_released,
                COUNT(l.listing_id) as active_listings,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price,
                MIN(l.date_posted) as first_seen,
                MAX(l.date_posted) as last_seen
            FROM gpu_reference g
            JOIN listings l ON g.id = l.matched_gpu_id
            WHERE l.category = 'gpu'
                AND l.confidence_score >= 0.70
                {date_clause}
                {active_time_clause}
                {flagged_clause}
            GROUP BY g.id, g.vendor, g.model, g.vram_gb, g.year_released
            HAVING COUNT(l.listing_id) >= 1
            ORDER BY {order_by}
        """)

        models = cursor.fetchall()

        # Format VRAM
        formatted_models = []
        for model in models:
            model_dict = dict(model)
            model_dict['vram_gb'] = format_vram(model_dict['vram_gb'])
            formatted_models.append(model_dict)

        cursor.close()

        return jsonify(formatted_models)


@app.route('/api/cpus/platform-stats')
@cache_control(max_age=30)
def get_cpu_platform_stats():
    """Get CPU market stats grouped by platform and socket.

    Returns:
        {
          "platform_stats": [{"platform": "Intel", "count": 234, "avg_price": 92.1}, ...],
          "socket_stats": [{"socket": "AM4", "count": 111, "avg_price": 70.0}, ...]
        }
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_filter = request.args.get('time', 'all_time')
            show_active = request.args.get('active', 'true').lower() == 'true'
            time_clause = get_time_filter_sql(time_filter, 'l')

            active_clause = " AND l.is_active = true" if show_active else ""

            # Platform / Socket distribution for CPU listings with matched reference
            cursor.execute(f"""
                SELECT
                    c.socket,
                    COUNT(*) AS count,
                    ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price
                FROM listings l
                JOIN cpu_reference c ON l.matched_cpu_id = c.id
                WHERE l.category = 'cpu'
                  {active_clause}
                  AND l.cpu_confidence_score >= 0.70
                  AND c.socket IS NOT NULL AND c.socket != ''
                  {time_clause}
                GROUP BY c.socket
                ORDER BY count DESC
            """)
            socket_rows = cursor.fetchall()

            platform_stats = {'Intel': {'count': 0, 'avg_total': 0.0}, 'AMD': {'count': 0, 'avg_total': 0.0}, 'Other': {'count': 0, 'avg_total': 0.0}}
            socket_stats = []
            for row in socket_rows:
                r = convert_decimal_to_float(dict(row))
                socket = (r.get('socket') or 'Unknown').strip()
                count = int(r.get('count') or 0)
                avg_price = float(r.get('avg_price') or 0)
                socket_stats.append({'socket': socket, 'count': count, 'avg_price': avg_price})

                socket_lower = socket.lower()
                if socket_lower.startswith('lga') or ('intel' in socket_lower and 'socket' in socket_lower):
                    platform = 'Intel'
                elif socket_lower.startswith('am') or socket_lower in ('tr4', 'strx4'):
                    platform = 'AMD'
                else:
                    platform = 'Other'

                platform_stats[platform]['count'] += count
                platform_stats[platform]['avg_total'] += count * avg_price

            platform_stats_list = []
            for platform, data in platform_stats.items():
                total_count = data['count']
                avg_price = round(data['avg_total'] / total_count, 2) if total_count > 0 else 0
                platform_stats_list.append({'platform': platform, 'count': total_count, 'avg_price': avg_price})
            platform_stats_list.sort(key=lambda x: x['count'], reverse=True)

            cursor.close()

            return jsonify({
                'platform_stats': platform_stats_list,
                'socket_stats': socket_stats
            })

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/cpus/price-history-monthly')
@cache_control(max_age=30)
def get_cpu_price_history_monthly():
    """Get average CPU price per month over time.

    Returns a list of monthly aggregate rows with average price and listing count.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            active_clause = "AND l.is_active = true" if show_active else ""

            cursor.execute(f"""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', ph.recorded_at), 'YYYY-MM') AS month,
                    ROUND(AVG(ph.price_eur)::numeric, 2) AS avg_price,
                    COUNT(DISTINCT ph.listing_id) AS listing_count
                FROM price_history ph
                JOIN listings l ON l.listing_id = ph.listing_id
                WHERE l.category = 'cpu'
                  {active_clause}
                GROUP BY DATE_TRUNC('month', ph.recorded_at)
                ORDER BY DATE_TRUNC('month', ph.recorded_at) ASC
            """)
            rows = [convert_decimal_to_float(dict(row)) for row in cursor.fetchall()]

            cursor.close()

            return jsonify(rows)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/cpus/price-history-by-model')
@cache_control(max_age=60)
def get_cpu_price_history_by_model():
    """Per-CPU-model price-over-time series, used by the listing popup's
    Market Price Analysis card.

    Aggregates `price_history` rows for every listing whose
    `matched_cpu_id` equals the requested id, bucketed by month, and
    returns [{month, avg_price, listing_count}, ...] sorted ascending.

    Query params:
      matched_cpu_id (int, required) — cpu_reference.id
      months (int, default 24) — how many months back to look
    """
    matched_cpu_id = request.args.get('matched_cpu_id', '').strip()
    if not matched_cpu_id or not matched_cpu_id.isdigit():
        return jsonify({'error': 'matched_cpu_id is required and must be an integer'}), 400
    matched_cpu_id_int = int(matched_cpu_id)

    months_param = request.args.get('months', '24').strip()
    try:
        months = max(1, min(120, int(months_param)))
    except ValueError:
        months = 24

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Cast `months` to int to avoid SQL injection via the INTERVAL
            # arithmetic. We use `make_interval(months => %s)` so PostgreSQL
            # treats it as an integer, not a string template.
            cursor.execute("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', ph.recorded_at), 'YYYY-MM') AS month,
                    ROUND(AVG(ph.price_eur)::numeric, 2) AS avg_price,
                    COUNT(DISTINCT ph.listing_id) AS listing_count
                FROM price_history ph
                JOIN listings l ON l.listing_id = ph.listing_id
                WHERE l.category = 'cpu'
                  AND l.matched_cpu_id = %s
                  AND ph.recorded_at >= NOW() - make_interval(months => %s)
                GROUP BY DATE_TRUNC('month', ph.recorded_at)
                ORDER BY DATE_TRUNC('month', ph.recorded_at) ASC
            """, (matched_cpu_id_int, months))
            rows = [convert_decimal_to_float(dict(row)) for row in cursor.fetchall()]
            return jsonify({
                'matched_cpu_id': matched_cpu_id_int,
                'months': months,
                'series': rows
            })
        except Exception as e:
            return jsonify({'error': str(e), 'series': []}), 500
        finally:
            cursor.close()


@app.route('/api/cpu-models')
@cache_control(max_age=30)
def get_cpu_models():
    """Get aggregated CPU model statistics with sorting."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        sort = request.args.get('sort', 'price_desc')

        order_map = {
            'price_desc': 'avg_price DESC',
            'price_asc': 'avg_price ASC',
            'listings_desc': 'active_listings DESC',
            'listings_asc': 'active_listings ASC'
        }
        order_by = order_map.get(sort, 'avg_price DESC')

        time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

        cursor.execute(f"""
            SELECT
                c.id,
                c.producer,
                c.cpu_name,
                c.processor_number,
                c.cores,
                c.threads,
                c.socket,
                COUNT(l.listing_id) as active_listings,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price
            FROM cpu_reference c
            JOIN listings l ON c.id = l.matched_cpu_id
            WHERE l.category = 'cpu'
                AND l.cpu_confidence_score >= 0.70
                {time_clause}
                {flagged_clause}
            GROUP BY c.id, c.producer, c.cpu_name, c.processor_number, c.cores, c.threads, c.socket
            HAVING COUNT(l.listing_id) >= 1
            ORDER BY {order_by}
        """)

        models = cursor.fetchall()

        cursor.close()

        return jsonify([convert_decimal_to_float(dict(row)) for row in models])


@app.route('/api/gpu-model-stats')
@cache_control(max_age=30)
def get_gpu_model_stats():
    """Get GPU model statistics sorted by most listed (for stats bar)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        time_filter = request.args.get('time', 'all_time')
        use_active_avg = request.args.get('use_active_avg', 'false').lower() == 'true'
        time_clause = get_time_filter_sql(time_filter, 'l')
        flagged_clause = "AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)" if use_active_avg else ""

        cursor.execute(f"""
            SELECT
                g.vendor,
                g.model,
                COUNT(l.listing_id) as count,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price,
                g.vram_gb
            FROM gpu_reference g
            JOIN listings l ON g.id = l.matched_gpu_id
            WHERE l.category = 'gpu'
                AND l.confidence_score >= 0.70
                {time_clause}
                {flagged_clause}
            GROUP BY g.vendor, g.model, g.vram_gb
            HAVING COUNT(l.listing_id) >= 1
            ORDER BY COUNT(l.listing_id) DESC, avg_price ASC
        """)

        models = cursor.fetchall()

        cursor.close()

        return jsonify({'models': [dict(row) for row in models]})


@app.route('/api/ssd-models')
@cache_control(max_age=30)
def get_ssd_models():
    """Get aggregated SSD model statistics with sorting."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        sort = request.args.get('sort', 'price_desc')

        order_map = {
            'price_desc': 'avg_price DESC',
            'price_asc': 'avg_price ASC',
            'listings_desc': 'active_listings DESC',
            'listings_asc': 'active_listings ASC'
        }
        order_by = order_map.get(sort, 'avg_price DESC')

        time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

        cursor.execute(f"""
            SELECT
                s.id,
                s.brand,
                s.model,
                s.capacity_gb,
                s.interface,
                s.form_factor,
                s.read_speed_mb,
                s.write_speed_mb,
                COUNT(l.listing_id) as active_listings,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price,
                MIN(l.date_posted) as first_seen,
                MAX(l.date_posted) as last_seen
            FROM ssd_reference s
            JOIN listings l ON s.id = l.matched_ssd_id
            WHERE l.category = 'ssd'
                AND l.ssd_confidence_score >= 0.70
                {time_clause}
                {flagged_clause}
            GROUP BY s.id, s.brand, s.model, s.capacity_gb, s.interface, s.form_factor, s.read_speed_mb, s.write_speed_mb
            HAVING COUNT(l.listing_id) >= 1
            ORDER BY {order_by}
        """)

        models = cursor.fetchall()

        # Add classified interface_type to each model dict
        formatted_models = []
        for model in models:
            model_dict = convert_decimal_to_float(dict(model))
            model_dict['interface_type'] = _classify_ssd_interface_type(model_dict.get('interface'))
            formatted_models.append(model_dict)

        cursor.close()

        return jsonify(formatted_models)


@app.route('/api/ssd-statistics')
@cache_control(max_age=30)
def get_ssd_statistics():
    """Get SSD statistics for charts and dashboard."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        time_filter = request.args.get('time', 'all_time')
        active_only = request.args.get('active', 'true').lower() == 'true'
        time_clause = get_time_filter_sql(time_filter, 'l')
        active_clause = 'AND l.is_active = true' if active_only else ''

        # Get basic stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_listings,
                COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                SUM(capacity_gb) as total_capacity
            FROM listings l
            WHERE l.category = 'ssd'
            {active_clause}
            {time_clause}
        """
        )

        stats = dict(cursor.fetchone())

        # Calculate avg cost per GB
        cursor.execute(f"""
            SELECT
                CASE WHEN SUM(capacity_gb) > 0
                     THEN ROUND((SUM(price_eur) / SUM(capacity_gb))::numeric, 3)
                     ELSE 0
                END as avg_cost_per_gb
            FROM listings l
            WHERE l.category = 'ssd' AND capacity_gb IS NOT NULL
            {active_clause}
            {time_clause}
        """)

        cost_result = cursor.fetchone()
        stats['avg_cost_per_gb'] = cost_result['avg_cost_per_gb'] or 0

        # Get capacity distribution for chart
        cursor.execute(f"""
            SELECT
                capacity_gb,
                COUNT(*) as listing_count,
                ROUND(AVG(price_eur)::numeric, 2) as avg_price
            FROM listings l
            WHERE l.category = 'ssd' AND capacity_gb IS NOT NULL
            {active_clause}
            {time_clause}
            GROUP BY capacity_gb
            ORDER BY capacity_gb ASC
        """)

        capacity_distribution = [dict(row) for row in cursor.fetchall()]
        stats['capacity_distribution'] = capacity_distribution

        # Get capacity distribution grouped by interface type for overlay chart
        cursor.execute(f"""
            SELECT
                l.capacity_gb,
                CASE
                    WHEN COALESCE(s.interface, '') ILIKE '%%SATA%%' THEN 'SATA'
                    WHEN COALESCE(s.interface, '') ILIKE '%%NVMe%%'
                         OR COALESCE(s.interface, '') ILIKE '%%PCIe%%'
                         OR COALESCE(s.interface, '') ILIKE '%%PCI-E%%' THEN 'NVMe'
                    ELSE 'Other'
                END as interface_type,
                COUNT(*) as listing_count,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
            FROM listings l
            LEFT JOIN ssd_reference s ON l.matched_ssd_id = s.id
            WHERE l.category = 'ssd' AND l.capacity_gb IS NOT NULL
            {active_clause}
            {time_clause}
            GROUP BY l.capacity_gb, interface_type
            ORDER BY l.capacity_gb ASC, interface_type ASC
        """)
        capacity_distribution_by_interface = [dict(row) for row in cursor.fetchall()]
        stats['capacity_distribution_by_interface'] = capacity_distribution_by_interface

        cursor.close()

        return jsonify(stats)


@app.route('/api/ssd-cost-per-gb-timeline')
@cache_control(max_age=30)
def get_ssd_cost_per_gb_timeline():
    """Get average cost per GB over months for SSDs."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_filter = request.args.get('time', 'all_time')

            query = """
                SELECT
                    DATE_TRUNC('month', COALESCE(l.date_posted, l.first_seen_at, l.created_at))::date as month,
                    COUNT(*) as listing_count,
                    ROUND((SUM(l.price_eur) / NULLIF(SUM(l.capacity_gb), 0))::numeric, 4) as avg_cost_per_gb,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    SUM(l.capacity_gb) as total_capacity_gb
                FROM listings l
                WHERE l.category = 'ssd'
                  AND l.is_active = true
                  AND l.capacity_gb IS NOT NULL
                  AND l.capacity_gb > 0
                  AND l.price_eur IS NOT NULL
                  AND l.price_eur > 0
            """

            if time_filter == 'month':
                query += " AND COALESCE(l.date_posted, l.first_seen_at, l.created_at) >= NOW() - INTERVAL '30 days'"
            elif time_filter == 'week':
                query += " AND COALESCE(l.date_posted, l.first_seen_at, l.created_at) >= NOW() - INTERVAL '7 days'"

            query += """
                GROUP BY month
                ORDER BY month ASC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            cursor.close()

            return jsonify([{
                'month': str(row['month']),
                'listing_count': row['listing_count'],
                'avg_cost_per_gb': float(row['avg_cost_per_gb']) if row['avg_cost_per_gb'] is not None else 0,
                'avg_price': float(row['avg_price']) if row['avg_price'] is not None else 0,
                'total_capacity_gb': float(row['total_capacity_gb']) if row['total_capacity_gb'] is not None else 0
            } for row in rows])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/ssds/<listing_id>')
@cache_control(max_age=30)
def get_ssd_detail(listing_id):
    """Get detailed SSD listing information."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.description,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.first_seen_at,
                    l.created_at,
                    l.ssd_confidence_score,
                    l.ssd_match_method,
                    l.matched_ssd_id,
                    l.capacity_gb,
                    l.local_image_path,
                    l.image_url,
                    l.listing_url,
                    s.brand as ssd_brand,
                    s.model as ssd_model,
                    s.capacity_gb as ssd_capacity_gb,
                    s.interface,
                    s.form_factor,
                    s.read_speed_mb,
                    s.write_speed_mb,
                    s.nand_type,
                    s.controller
                FROM listings l
                LEFT JOIN ssd_reference s ON l.matched_ssd_id = s.id
                WHERE l.listing_id = %s AND l.category = 'ssd'
            """, (listing_id,))

            listing = cursor.fetchone()

            if not listing:
                return jsonify({'success': False, 'error': 'Listing not found'}), 404

            return jsonify({'success': True, 'listing': dict(listing)})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()


@app.route('/api/ssd-details/<int:ssd_id>')
@cache_control(max_age=30)
def get_ssd_details_by_id(ssd_id):
    """Get SSD reference details by ID (for flagging)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT
                    id,
                    brand,
                    model,
                    capacity_gb,
                    interface,
                    form_factor,
                    read_speed_mb,
                    write_speed_mb,
                    nand_type,
                    controller
                FROM ssd_reference
                WHERE id = %s
            """, (ssd_id,))

            ssd = cursor.fetchone()

            if not ssd:
                return jsonify({'success': False, 'error': 'SSD not found'}), 404

            return jsonify({'success': True, 'ssd': dict(ssd)})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()




def _classify_ssd_interface_type(interface: Optional[str], description: Optional[str] = None) -> str:
    """Classify SSD interface string into SATA, NVMe, Portable, or Other."""
    if not interface:
        return 'Other'

    # Check description first for portable indicators (case-insensitive)
    desc = (description or '').lower()
    portable_desc_phrases = [
        'portable', 'внешний', 'external', 'usb 3.2 gen 2x2', 'usb 3.2 gen 2x1',
        'usb 3.2', 'usb 3.1', 'usb 3.0', 'usb-c'
    ]
    for phrase in portable_desc_phrases:
        if phrase in desc:
            return 'Portable'

    ui = interface.upper()

    # Portable interface strings
    if any(p in ui for p in ['USB', 'THUNDERBOLT', 'EXTERNAL']):
        return 'Portable'

    if 'SATA' in ui:
        return 'SATA'
    if 'NVME' in ui or 'PCIE' in ui or 'PCI-E' in ui:
        return 'NVMe'
    return 'Other'
@app.route('/api/ssds')
@cache_control(max_age=30)
def get_ssds():
    """Get SSD listings with filters and sorting."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get query parameters
            show_active = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('min_confidence', 0))
            time_filter = request.args.get('time', 'all_time')
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            brand_filter = request.args.get('brand', '')
            model_filter = request.args.get('model', '')
            capacity_filter = request.args.get('capacity', '')
            location = request.args.get('location', '').strip()
            interface_type = request.args.get('interface_type', '').strip()

            source_filter = request.args.get('source', '').strip()

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.first_seen_at,
                    l.ssd_confidence_score,
                    l.ssd_match_method,
                    l.matched_ssd_id,
                    l.capacity_gb,
                    l.local_image_path,
                    l.description,
                    s.brand as ssd_brand,
                    s.model as ssd_model,
                    s.capacity_gb as ssd_capacity_gb,
                    s.interface,
                    s.form_factor,
                    l.image_url,
                    l.listing_url,
                    l.source,
                    -- True when there is a price_history row showing a decrease
                    -- from the previous snapshot. Used for the "Price drop" badge.
                    EXISTS (
                        SELECT 1 FROM price_history ph2
                        WHERE ph2.listing_id ~ ('^' || REPLACE(l.listing_id, '_v[0-9]+$', '') || '(_v[0-9]+)?$')
                          AND ph2.change_type = 'decrease'
                    ) AS has_price_decreased
                FROM listings l
                LEFT JOIN ssd_reference s ON l.matched_ssd_id = s.id
                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                WHERE l.category = 'ssd'
                    AND fl.listing_id IS NULL
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            if source_filter and source_filter != 'all':
                # Front-end sends the canonical source key (ss.com /
                # andelemandele / facebook_extension). Filter directly on the
                # listings.source column; safe against injection because
                # RealDictCursor uses parameterised queries.
                query += " AND l.source = %s"
                params.append(source_filter)
            query += _unmatched_filter_sql('ssd')
            if min_confidence > 0:
                query += " AND l.ssd_confidence_score >= %s"
                params.append(min_confidence)
            if brand_filter:
                query += " AND s.brand ILIKE %s"
                params.append(f'%{brand_filter}%')
            if model_filter:
                query += " AND s.model ILIKE %s"
                params.append(f'%{model_filter}%')
            if location:
                query += " AND COALESCE(l.seller_location, '') ILIKE %s"
                params.append(f'%{location}%')
            if interface_type and interface_type in ('SATA', 'NVMe', 'Portable', 'Other'):
                query += """ AND CASE
                    WHEN COALESCE(s.interface, '') ILIKE '%%USB%%'
                         OR COALESCE(s.interface, '') ILIKE '%%THUNDERBOLT%%'
                         OR COALESCE(s.interface, '') ILIKE '%%EXTERNAL%%'
                         OR COALESCE(l.description, '') ILIKE '%%Portable%%'
                         OR COALESCE(l.description, '') ILIKE '%%USB%%'
                         OR COALESCE(l.description, '') ILIKE '%%Внешний%%'
                         OR COALESCE(l.description, '') ILIKE '%%External%%' THEN 'Portable'
                    WHEN COALESCE(s.interface, '') ILIKE '%%SATA%%' THEN 'SATA'
                    WHEN COALESCE(s.interface, '') ILIKE '%%NVMe%%'
                         OR COALESCE(s.interface, '') ILIKE '%%PCIe%%'
                         OR COALESCE(s.interface, '') ILIKE '%%PCI-E%%' THEN 'NVMe'
                    ELSE 'Other'
                END = %s"""
                params.append(interface_type)
            if capacity_filter:
                # Map the dropdown values to actual capacity ranges
                # "128" -> 120-128GB, "256" -> 240-256GB, "512" -> 480-512GB, etc.
                capacity_ranges = {
                    '128': (120, 128),
                    '256': (240, 256),
                    '512': (480, 512),
                    '1024': (960, 1024),
                    '2048': (1900, 2048),
                    '4096': (3800, 4096),  # 4TB
                    '8192': (7600, 8192),  # 8TB
                    '16384': (15000, 32768),  # 16TB+
                }

                # Check if it's a known range key
                if capacity_filter in capacity_ranges:
                    min_cap, max_cap = capacity_ranges[capacity_filter]
                    query += " AND (COALESCE(l.capacity_gb, s.capacity_gb) BETWEEN %s AND %s)"
                    params.extend([min_cap, max_cap])
                else:
                    # Handle raw range format like "480-512GB" or "480-512" or "512GB (480-512GB)"
                    capacity_str = capacity_filter.replace('GB', '').replace('gb', '').strip()
                    range_match = re.search(r'\((\d+)[-\s]*(\d+)\)', capacity_filter)
                    if range_match:
                        try:
                            min_cap = int(range_match.group(1))
                            max_cap = int(range_match.group(2))
                            query += " AND (COALESCE(l.capacity_gb, s.capacity_gb) BETWEEN %s AND %s)"
                            params.extend([min_cap, max_cap])
                        except ValueError:
                            pass
                    elif '-' in capacity_str:
                        parts = capacity_str.split('-')
                        if len(parts) == 2:
                            try:
                                min_cap = int(parts[0])
                                max_cap = int(parts[1])
                                query += " AND (COALESCE(l.capacity_gb, s.capacity_gb) BETWEEN %s AND %s)"
                                params.extend([min_cap, max_cap])
                            except ValueError:
                                pass
                    else:
                        # Single capacity
                        try:
                            cap = int(capacity_str)
                            query += " AND (COALESCE(l.capacity_gb, s.capacity_gb) = %s)"
                            params.append(cap)
                        except ValueError:
                            pass

            query += get_time_filter_sql(time_filter)

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"

            try:
                cursor.execute(query, params)
                listings = cursor.fetchall()

                # Get the most recent first_seen date for "new" badge calculation
                cursor.execute("""
                    SELECT MAX(first_seen_at::date) as last_date
                    FROM listings
                    WHERE category = 'ssd'
                """)
                last_date_result = cursor.fetchone()
                last_date = last_date_result['last_date'] if last_date_result else None

                # Mark as new
                enhanced_listings = []
                for listing in listings:
                    listing_dict = convert_decimal_to_float(dict(listing))
                    listing_dict['interface_type'] = _classify_ssd_interface_type(listing_dict.get('interface'), listing_dict.get('description'))
                    if last_date and listing_dict.get('first_seen_at'):
                        first_seen = listing_dict['first_seen_at']
                        listing_dict['is_new'] = (first_seen.date() if hasattr(first_seen, 'date') else first_seen) == last_date
                    else:
                        listing_dict['is_new'] = False
                    enhanced_listings.append(listing_dict)

                # Compute model-level price stats (is_unicorn, price_stats) in a
                # single GROUP BY query, then attach to each listing. These
                # power the UNICORN and STEAL badges on the SSD page.
                ssd_ids = [l['matched_ssd_id'] for l in enhanced_listings if l.get('matched_ssd_id')]
                if ssd_ids:
                    cursor.execute("""
                        SELECT
                            matched_ssd_id,
                            COUNT(*) AS listing_count,
                            ROUND(AVG(price_eur)::numeric, 2) AS avg_price,
                            MIN(price_eur) AS min_price,
                            MAX(price_eur) AS max_price
                        FROM listings
                        WHERE category = 'ssd'
                          AND is_active = true
                          AND matched_ssd_id = ANY(%s)
                        GROUP BY matched_ssd_id
                    """, (ssd_ids,))
                    ssd_stats = {row['matched_ssd_id']: dict(row) for row in cursor.fetchall()}
                else:
                    ssd_stats = {}

                for listing_dict in enhanced_listings:
                    stats = ssd_stats.get(listing_dict.get('matched_ssd_id'))
                    if stats and stats.get('listing_count') is not None:
                        count = int(stats['listing_count'])
                        listing_dict['is_unicorn'] = count == 1
                        if count > 1:
                            avg = float(stats['avg_price']) if stats['avg_price'] is not None else None
                            min_p = float(stats['min_price']) if stats['min_price'] is not None else None
                            max_p = float(stats['max_price']) if stats['max_price'] is not None else None
                            listing_dict['price_stats'] = {
                                'avg': avg,
                                'min': min_p,
                                'max': max_p,
                                'count': count,
                                'below_avg': (listing_dict.get('price_eur') is not None and avg is not None
                                              and float(listing_dict['price_eur']) < avg),
                            }
                        else:
                            listing_dict['price_stats'] = None
                    else:
                        listing_dict['is_unicorn'] = False
                        listing_dict['price_stats'] = None

                # Capacity-level market stats — average / min / max / count
                # across ALL listings (active + inactive) for the same
                # capacity. Powers the "Market price position" column so
                # users can see how a specific drive's price compares to
                # the broader market at that capacity, not just to the
                # exact same model.
                capacity_keys = set()
                for lst in enhanced_listings:
                    cg = lst.get('capacity_gb') or lst.get('ssd_capacity_gb')
                    if cg:
                        capacity_keys.add(int(cg))
                if capacity_keys:
                    cursor.execute("""
                        SELECT
                            COALESCE(l.capacity_gb, s.capacity_gb) AS cap_gb,
                            COUNT(*) AS listing_count,
                            ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price,
                            MIN(l.price_eur) AS min_price,
                            MAX(l.price_eur) AS max_price,
                            SUM(CASE WHEN l.is_active = true THEN 1 ELSE 0 END) AS active_count
                        FROM listings l
                        LEFT JOIN ssd_reference s ON l.matched_ssd_id = s.id
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ssd'
                          AND fl.listing_id IS NULL
                          AND COALESCE(l.capacity_gb, s.capacity_gb) = ANY(%s)
                          AND l.price_eur IS NOT NULL
                          AND l.price_eur > 0
                        GROUP BY COALESCE(l.capacity_gb, s.capacity_gb)
                    """, (list(capacity_keys),))
                    cap_stats = {}
                    for row in cursor.fetchall():
                        cap_stats[int(row['cap_gb'])] = {
                            'avg': float(row['avg_price']) if row['avg_price'] else None,
                            'min': float(row['min_price']) if row['min_price'] else None,
                            'max': float(row['max_price']) if row['max_price'] else None,
                            'count': int(row['listing_count']),
                            'active_count': int(row['active_count']),
                        }
                    for lst in enhanced_listings:
                        cg = lst.get('capacity_gb') or lst.get('ssd_capacity_gb')
                        if cg and int(cg) in cap_stats:
                            cs = cap_stats[int(cg)]
                            cur = lst.get('price_eur')
                            try:
                                cur_f = float(cur) if cur is not None else None
                            except (TypeError, ValueError):
                                cur_f = None
                            avg = cs['avg']
                            below_avg = (cur_f is not None and avg is not None
                                         and cur_f < avg)
                            lst['market_position'] = {
                                'avg': avg,
                                'min': cs['min'],
                                'max': cs['max'],
                                'count': cs['count'],
                                'active_count': cs['active_count'],
                                'below_avg': below_avg,
                            }
                        else:
                            lst['market_position'] = None

                cursor.close()

                return jsonify(enhanced_listings)

            except Exception as e:
                cursor.close()
                return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Database connection failed: {str(e)}'}), 500



@app.route('/ssd')
def ssd_page():
    """SSD listings page."""
    return render_template('ssd.html')


@app.route('/api/unmatched')
@cache_control(max_age=30)
def get_unmatched():
    """Get unmatched listings that need manual review."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        category = request.args.get('category', 'all')  # gpu, cpu, all

        query = """
            SELECT
                l.listing_id,
                l.title,
                l.price_eur,
                l.seller_location,
                l.date_posted,
                l.is_active,
                l.category,
                l.image_url,
                l.listing_url,
                l.matched_gpu_id,
                l.matched_cpu_id,
                l.matched_ssd_id,
                l.confidence_score,
                l.cpu_confidence_score,
                l.ssd_confidence_score
            FROM listings l
            WHERE (
                (l.category = 'gpu' AND l.matched_gpu_id IS NULL)
                OR (l.category = 'cpu' AND l.matched_cpu_id IS NULL)
                OR (l.category = 'ssd' AND l.matched_ssd_id IS NULL)
            )
        """

        if category != 'all':
            query += f" AND l.category = '{category}'"

        query += " ORDER BY l.date_posted DESC LIMIT 100"

        cursor.execute(query)
        listings = cursor.fetchall()

        # Get available models for matching
        cursor.execute("SELECT id, vendor, model FROM gpu_reference ORDER BY vendor, model")
        gpu_models = cursor.fetchall()

        cursor.execute("SELECT id, producer, cpu_name FROM cpu_reference ORDER BY cpu_name")
        cpu_models = cursor.fetchall()

        cursor.execute("SELECT id, brand, model, capacity_gb FROM ssd_reference ORDER BY brand, model")
        ssd_models = cursor.fetchall()

        cursor.close()

        return jsonify({
            'listings': [dict(row) for row in listings],
            'gpu_models': [dict(row) for row in gpu_models],
            'cpu_models': [dict(row) for row in cpu_models],
            'ssd_models': [dict(row) for row in ssd_models]
        })


@app.route('/api/update-match', methods=['POST'])
def update_match():
    """Update listing match manually."""
    data = request.get_json()

    listing_id = data.get('listing_id')
    action = data.get('action')  # 'match_gpu', 'match_cpu', 'ignore'
    model_id = data.get('model_id')  # For match actions

    if not listing_id or not action:
        return jsonify({'error': 'Missing required fields'}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            if action == 'match_gpu' and model_id:
                cursor.execute("""
                    UPDATE listings
                    SET matched_gpu_id = %s,
                        confidence_score = 1.0,
                        match_method = 'manual',
                        is_active = true
                    WHERE listing_id = %s AND category = 'gpu'
                """, (model_id, listing_id))
            elif action == 'match_cpu' and model_id:
                cursor.execute("""
                    UPDATE listings
                    SET matched_cpu_id = %s,
                        cpu_confidence_score = 1.0,
                        cpu_match_method = 'manual',
                        is_active = true
                    WHERE listing_id = %s AND category = 'cpu'
                """, (model_id, listing_id))
            elif action == 'ignore':
                cursor.execute("""
                    UPDATE listings
                    SET is_active = false
                    WHERE listing_id = %s
                """, (listing_id,))
            else:
                return jsonify({'error': 'Invalid action'}), 400

            conn.commit()
            cursor.close()

            return jsonify({'success': True, 'message': 'Listing updated successfully'})

        except Exception as e:
            conn.rollback()
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/computers')
def computers_page():
    """Computer listings page."""
    return render_template('computers.html')


def compute_scores(listing):
    """Compute a composite performance score and value score for a computer listing.

    The score is on a 0-100 scale where:
      - Top-end CPU (R23 ~30k / PassMark ~50k) ≈ 40 pts
      - Top-end GPU (G3D ~30k)               ≈ 40 pts
      - 32GB DDR5 RAM                        ≈  8 pts
      - 4TB SSD                              ≈  8 pts
    A perfectly maxed build scores ~96. Mid-range gaming builds land in
    the 25-45 range. The previous formula could produce scores like
    146 ("146/100") because the components were never scaled against a
    100-point ceiling — `cpu_score/1000 * 15` for an i9-13900K is
    `~480`, and 0.4 of that alone is 192. Clamp at 100.
    """
    # CPU score: prefer Cinebench R23 multi, fall back to PassMark
    cpu_score = None
    r23_multi = listing.get('cpu_r23_multi')
    passmark = listing.get('cpu_passmark')
    if r23_multi:
        try:
            cpu_score = float(r23_multi)
        except Exception:
            pass
    if cpu_score is None and passmark:
        try:
            cpu_score = float(passmark)
        except Exception:
            pass
    # GPU score: G3D Mark
    gpu_score = None
    g3d = listing.get('gpu_g3d_mark')
    if g3d:
        try:
            gpu_score = float(g3d)
        except Exception:
            pass
    # RAM score: capacity * speed factor, capped at 8 pts (32GB DDR5)
    ram_capacity = listing.get('ram_capacity') or 0
    try:
        ram_capacity = float(ram_capacity)
    except Exception:
        ram_capacity = 0
    ram_type = (listing.get('ram_type') or '').lower()
    ram_speed_factor = 1.0
    if 'ddr5' in ram_type:
        ram_speed_factor = 1.5
    elif 'ddr4' in ram_type:
        ram_speed_factor = 1.0
    elif 'ddr3' in ram_type:
        ram_speed_factor = 0.7
    # Scale: 16GB DDR4 = 8pts, 32GB DDR5 = 12pts, 64GB DDR5 = 24pts → cap 8
    ram_raw = ram_capacity * ram_speed_factor * 0.5
    ram_score = min(8.0, ram_raw)

    # SSD score: capacity, capped at 8 pts (4TB)
    ssd_capacity = listing.get('ssd_capacity') or 0
    try:
        ssd_capacity = float(ssd_capacity)
    except Exception:
        ssd_capacity = 0
    # Scale: 1TB ≈ 2pts, 2TB ≈ 4pts, 4TB ≈ 8pts
    ssd_raw = ssd_capacity / 500.0
    ssd_score = min(8.0, ssd_raw)

    # CPU 0-40 (R23 30000 = 40, PassMark 50000 = 40 — whichever's higher wins)
    cpu_raw = 0
    if cpu_score:
        # R23 and PassMark both ~50k at the top; pick the best projection
        r23_norm = min(40.0, (cpu_score / 30000.0) * 40.0) if r23_multi else 0
        pm_norm = min(40.0, (cpu_score / 50000.0) * 40.0) if passmark else 0
        # Whichever metric is being used contributes
        cpu_raw = max(r23_norm, pm_norm)

    # GPU 0-40 (G3D 30000 = 40)
    gpu_raw = 0
    if gpu_score:
        gpu_raw = min(40.0, (gpu_score / 30000.0) * 40.0)

    performance_score = round(min(100.0, cpu_raw + gpu_raw + ram_score + ssd_score), 1)
    price = listing.get('price_eur')
    value_score = round(performance_score / price, 3) if price and price > 0 else None
    return performance_score, value_score


@app.route('/api/computers')
@cache_control(max_age=30)
def get_computers():
    """Get computer listings."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if ram_reference table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'ram_reference'
                )
            """)
            ram_table_exists = cursor.fetchone()['exists']

            # Apply prebuilt filter from query string
            prebuilt_filter = request.args.get('prebuilt')
            prebuilt_clause = ""
            params = []
            if prebuilt_filter == 'true':
                prebuilt_clause = "AND cl.is_prebuilt = true"
            elif prebuilt_filter == 'false':
                prebuilt_clause = "AND cl.is_prebuilt = false"

            # Apply hide-unmatched filter (uses cl.* alias)
            computer_unmatched_clause = _unmatched_filter_sql('computer', 'cl')

            if ram_table_exists:
                query = f"""
                    SELECT
                        cl.listing_id,
                        cl.title,
                        cl.description,
                        cl.price_eur,
                        cl.seller_location,
                        cl.date_posted,
                        cl.first_seen_at,
                        cl.is_active,
                        cl.listing_url,
                        cl.image_url,
                        cl.build_type,
                        cl.is_prebuilt,
                        cl.components_total_eur,
                        cl.price_difference_eur,
                        cl.matched_cpu_id,
                        cl.matched_gpu_id,
                        cpu.producer as cpu_producer,
                        cpu.cpu_name,
                        cpu.socket as cpu_socket,
                        cpu.cores as cpu_cores,
                        cpu.threads as cpu_threads,
                        cpu.max_turbo_freq as cpu_max_turbo,
                        gpu.vendor as gpu_vendor,
                        gpu.model as gpu_model,
                        gpu.vram_gb as gpu_vram,
                        gpass.g3d_mark as gpu_g3d_mark,
                        gpass.g2d_mark as gpu_g2d_mark,
                        cpass.passmark_score as cpu_passmark,
                        cr23.cinebench_r23_multi as cpu_r23_multi,
                        ram.capacity_gb as ram_capacity,
                        ram.type as ram_type,
                        cl.ram_match_method,
                        cl.ssd_match_method,
                        ssd.capacity_gb as ssd_capacity
                    FROM computer_listings cl
                    LEFT JOIN cpu_reference cpu ON cl.matched_cpu_id = cpu.id
                    LEFT JOIN gpu_reference gpu ON cl.matched_gpu_id = gpu.id
                    LEFT JOIN gpu_reference_passmark gpass ON gpu.id = gpass.gpu_reference_id
                    LEFT JOIN cpu_benchmarks_passmark cpass ON cpu.normalized_name = cpass.cpu_name
                    LEFT JOIN cpu_benchmarks_r23 cr23 ON cpu.normalized_name = cr23.cpu_name
                    LEFT JOIN ram_reference ram ON cl.matched_ram_id = ram.id
                    LEFT JOIN ssd_reference ssd ON cl.matched_ssd_id = ssd.id
                    WHERE cl.is_active = true {prebuilt_clause}{computer_unmatched_clause}
                    ORDER BY cl.date_posted DESC
                    LIMIT 100
                """
            else:
                query = f"""
                    SELECT
                        cl.listing_id,
                        cl.title,
                        cl.description,
                        cl.price_eur,
                        cl.seller_location,
                        cl.date_posted,
                        cl.first_seen_at,
                        cl.is_active,
                        cl.listing_url,
                        cl.image_url,
                        cl.build_type,
                        cl.is_prebuilt,
                        cl.components_total_eur,
                        cl.price_difference_eur,
                        cl.matched_cpu_id,
                        cl.matched_gpu_id,
                        cpu.producer as cpu_producer,
                        cpu.cpu_name,
                        cpu.socket as cpu_socket,
                        cpu.cores as cpu_cores,
                        cpu.threads as cpu_threads,
                        cpu.max_turbo_freq as cpu_max_turbo,
                        gpu.vendor as gpu_vendor,
                        gpu.model as gpu_model,
                        gpu.vram_gb as gpu_vram,
                        gpass.g3d_mark as gpu_g3d_mark,
                        gpass.g2d_mark as gpu_g2d_mark,
                        cpass.passmark_score as cpu_passmark,
                        cr23.cinebench_r23_multi as cpu_r23_multi,
                        NULL as ram_capacity,
                        NULL as ram_type,
                        cl.ram_match_method,
                        cl.ssd_match_method,
                        ssd.capacity_gb as ssd_capacity
                    FROM computer_listings cl
                    LEFT JOIN cpu_reference cpu ON cl.matched_cpu_id = cpu.id
                    LEFT JOIN gpu_reference gpu ON cl.matched_gpu_id = gpu.id
                    LEFT JOIN gpu_reference_passmark gpass ON gpu.id = gpass.gpu_reference_id
                    LEFT JOIN cpu_benchmarks_passmark cpass ON cpu.normalized_name = cpass.cpu_name
                    LEFT JOIN cpu_benchmarks_r23 cr23 ON cpu.normalized_name = cr23.cpu_name
                    LEFT JOIN ssd_reference ssd ON cl.matched_ssd_id = ssd.id
                    WHERE cl.is_active = true {prebuilt_clause}{computer_unmatched_clause}
                    ORDER BY cl.date_posted DESC
                    LIMIT 100
                """

            cursor.execute(query)
            listings = cursor.fetchall()

            # Convert Decimal to float for JSON serialization and normalize fields
            listings_dict = []
            listing_ids = []
            for row in listings:
                row_dict = dict(row)
                if row_dict.get('price_eur') is not None:
                    row_dict['price_eur'] = float(row_dict['price_eur'])

                if row_dict.get('components_total_eur') is not None:
                    row_dict['components_total_eur'] = float(row_dict['components_total_eur'])
                if row_dict.get('price_difference_eur') is not None:
                    row_dict['price_difference_eur'] = float(row_dict['price_difference_eur'])

                # Normalize build_type from DB; fall back to a content-based heuristic if missing
                build_type = row_dict.get('build_type') or 'custom'
                if build_type not in ('custom', 'prebuilt', 'office', 'unknown'):
                    build_type = 'custom'
                row_dict['build_type'] = build_type
                row_dict['is_prebuilt'] = bool(row_dict.get('is_prebuilt')) or build_type == 'prebuilt'
                row_dict['pc_type'] = build_type

                # Fallback: derive SSD capacity from ssd_match_method for generic/fallback detections
                if not row_dict.get('ssd_capacity') and row_dict.get('ssd_match_method'):
                    capacity_match = re.search(r'(\d+)\s*GB', row_dict['ssd_match_method'], re.IGNORECASE)
                    if capacity_match:
                        row_dict['ssd_capacity'] = int(capacity_match.group(1))

                listing_ids.append(row_dict['listing_id'])
                listings_dict.append(row_dict)

            # Compute scores for each listing
            for listing_dict in listings_dict:
                perf, value = compute_scores(listing_dict)
                listing_dict['performance_score'] = perf
                listing_dict['value_score'] = value

            # Compute latest import date for NEW badge from computer_listings itself
            latest_first_seen = None
            try:
                cursor.execute("""
                    SELECT MAX(first_seen_at::date) as latest_date
                    FROM computer_listings
                    WHERE first_seen_at IS NOT NULL
                """)
                result = cursor.fetchone()
                latest_first_seen = result['latest_date'] if result and result['latest_date'] else None
            except Exception:
                pass

            # Compute peer-group price statistics by CPU+GPU combination
            peer_stats = {}
            try:
                cursor.execute("""
                    SELECT
                        COALESCE(cl.matched_cpu_id, 0) as matched_cpu_id,
                        COALESCE(cl.matched_gpu_id, 0) as matched_gpu_id,
                        ROUND(AVG(cl.price_eur)::numeric, 2) as avg_price,
                        MIN(cl.price_eur) as min_price,
                        MAX(cl.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM computer_listings cl
                    WHERE cl.is_active = true
                    GROUP BY COALESCE(cl.matched_cpu_id, 0), COALESCE(cl.matched_gpu_id, 0)
                """)
                for row in cursor.fetchall():
                    key = (row['matched_cpu_id'], row['matched_gpu_id'])
                    peer_stats[key] = dict(row)
            except Exception:
                pass

            # Fetch per-listing price history stats for BUY badge (all-time low + variation)
            history_stats = {}
            if listing_ids:
                try:
                    cursor.execute("""
                        SELECT
                            listing_id,
                            MIN(price_eur) as min_price,
                            MAX(price_eur) as max_price,
                            COUNT(DISTINCT price_eur) as distinct_prices
                        FROM price_history
                        WHERE listing_id = ANY(%s)
                        GROUP BY listing_id
                    """, (listing_ids,))
                    for row in cursor.fetchall():
                        history_stats[row['listing_id']] = dict(row)
                except Exception:
                    pass

            # Enhance listings with NEW flag, peer price stats, and BUY signal
            enhanced_listings = []
            for listing_dict in listings_dict:
                # NEW badge: listing first seen on the latest import date for computers
                if latest_first_seen and listing_dict.get('first_seen_at'):
                    fs = listing_dict['first_seen_at']
                    listing_date = fs.date() if hasattr(fs, 'date') else fs
                    listing_dict['is_new'] = listing_date == latest_first_seen
                else:
                    listing_dict['is_new'] = False

                # Peer-group price stats for STEAL badge
                cpu_id = listing_dict.get('matched_cpu_id') or 0
                gpu_id = listing_dict.get('matched_gpu_id') or 0
                peer_key = (cpu_id, gpu_id)
                current_price = listing_dict.get('price_eur')
                price_stats = {
                    'avg': None,
                    'min': None,
                    'max': None,
                    'below_avg': False,
                    'savings_pct': 0.0,
                    'percentile': 50.0,
                    'listing_count': 1,
                    'all_time_min': None,
                    'has_variation': False,
                }
                if peer_key in peer_stats:
                    stats = peer_stats[peer_key]
                    count = int(stats['listing_count']) if stats['listing_count'] else 0
                    avg_price = float(stats['avg_price']) if stats['avg_price'] is not None else 0.0
                    min_price = float(stats['min_price']) if stats['min_price'] is not None else 0.0
                    max_price = float(stats['max_price']) if stats['max_price'] is not None else 0.0
                    savings_pct = round((avg_price - current_price) / avg_price * 100, 1) if avg_price else 0.0
                    price_stats = {
                        'avg': avg_price,
                        'min': min_price,
                        'max': max_price,
                        'below_avg': current_price is not None and current_price < avg_price,
                        'savings_pct': savings_pct,
                        'percentile': round((current_price - min_price) / (max_price - min_price) * 100, 1)
                                      if max_price > min_price else 50.0,
                        'listing_count': count,
                        'all_time_min': None,
                        'has_variation': max_price > min_price,
                    }

                # BUY badge signal: current price equals all-time recorded minimum and history has variation
                hist = history_stats.get(listing_dict['listing_id'])
                all_time_min = None
                has_variation = False
                if hist:
                    hist_min = float(hist['min_price']) if hist['min_price'] is not None else None
                    hist_max = float(hist['max_price']) if hist['max_price'] is not None else None
                    all_time_min = hist_min
                    has_variation = (hist['distinct_prices'] or 0) > 1 or (hist_max is not None and hist_min is not None and hist_max > hist_min)
                price_stats['all_time_min'] = all_time_min
                price_stats['has_variation'] = price_stats['has_variation'] or has_variation
                listing_dict['price_stats'] = price_stats

                listing_dict['is_buy'] = (
                    current_price is not None and
                    all_time_min is not None and
                    current_price == all_time_min and
                    bool(has_variation)
                )

                enhanced_listings.append(listing_dict)

            # Apply client-side sorting if requested
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            if sort_by == 'score':
                enhanced_listings.sort(key=lambda x: x.get('performance_score') or 0, reverse=(sort_order != 'asc'))
            elif sort_by == 'value_score':
                enhanced_listings.sort(key=lambda x: x.get('value_score') or 0, reverse=(sort_order != 'asc'))
            elif sort_by == 'price':
                enhanced_listings.sort(key=lambda x: x.get('price_eur') or 0, reverse=(sort_order != 'asc'))

            cursor.close()
            return jsonify({'success': True, 'listings': enhanced_listings})
        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/<listing_id>')
@cache_control(max_age=30)
def get_computer_detail(listing_id):
    """Get computer listing details."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if ram_reference table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'ram_reference'
                )
            """)
            ram_table_exists = cursor.fetchone()['exists']

            # Check if motherboard_models table exists (the real reference table)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            mb_table_exists = cursor.fetchone()['exists']

            # Check if monitor_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'monitor_models'
                )
            """)
            monitor_table_exists = cursor.fetchone()['exists']

            mb_select = ''',
                        mb.id as motherboard_id, mb.brand as mb_brand, mb.model as mb_model, mb.socket as mb_socket, mb.chipset as mb_chipset,
                        cl.motherboard_match_method''' if mb_table_exists else ',\n                    NULL as motherboard_id, NULL as mb_brand, NULL as mb_model, NULL as mb_socket, NULL as mb_chipset, cl.motherboard_match_method'
            mb_join = 'LEFT JOIN motherboard_models mb ON cl.matched_motherboard_id = mb.id' if mb_table_exists else ''

            monitor_select = ''',
                        mon.id as mon_id, mon.brand as mon_brand, mon.model as mon_model, mon.size as mon_size, mon.resolution as mon_resolution, mon.refresh_rate as mon_refresh_rate, mon.panel_type as mon_panel_type,
                        cl.monitor_match_method, cl.monitor_included''' if monitor_table_exists else ',\n                    NULL as mon_id, NULL as mon_brand, NULL as mon_model, NULL as mon_size, NULL as mon_resolution, NULL as mon_refresh_rate, NULL as mon_panel_type, cl.monitor_match_method, cl.monitor_included'
            monitor_join = 'LEFT JOIN monitor_models mon ON cl.matched_monitor_id = mon.id' if monitor_table_exists else ''

            if ram_table_exists:
                query = """
                    SELECT cl.*,
                        cpu.id as cpu_id, cpu.producer as cpu_producer, cpu.cpu_name, cpu.processor_number, cpu.normalized_name,
                        cpu.socket as cpu_socket,
                        gpu.id as gpu_id, gpu.vendor as gpu_vendor, gpu.model as gpu_model, gpu.vram_gb,
                        gpass.g3d_mark as gpu_g3d_mark,
                        cpass.passmark_score as cpu_passmark,
                        cr23.cinebench_r23_multi as cpu_r23_multi,
                        ram.id as ram_id, ram.name as ram_name, ram.speed as ram_speed, ram.capacity_gb as ram_capacity, ram.type as ram_type,
                        ssd.id as ssd_id, ssd.brand as ssd_brand, ssd.model as ssd_model, ssd.capacity_gb as ssd_capacity,
                        cl.ram_match_method, cl.ssd_match_method
                        {mb_select}
                        {monitor_select}
                    FROM computer_listings cl
                    LEFT JOIN cpu_reference cpu ON cl.matched_cpu_id = cpu.id
                    LEFT JOIN gpu_reference gpu ON cl.matched_gpu_id = gpu.id
                    LEFT JOIN gpu_reference_passmark gpass ON gpu.id = gpass.gpu_reference_id
                    LEFT JOIN cpu_benchmarks_passmark cpass ON cpu.normalized_name = cpass.cpu_name
                    LEFT JOIN cpu_benchmarks_r23 cr23 ON cpu.normalized_name = cr23.cpu_name
                    LEFT JOIN ram_reference ram ON cl.matched_ram_id = ram.id
                    LEFT JOIN ssd_reference ssd ON cl.matched_ssd_id = ssd.id
                    {mb_join}
                    {monitor_join}
                    WHERE cl.listing_id = %s
                """.format(mb_select=mb_select, mb_join=mb_join, monitor_select=monitor_select, monitor_join=monitor_join)
            else:
                query = """
                    SELECT cl.*,
                        cpu.id as cpu_id, cpu.producer as cpu_producer, cpu.cpu_name, cpu.processor_number, cpu.normalized_name,
                        cpu.socket as cpu_socket,
                        gpu.id as gpu_id, gpu.vendor as gpu_vendor, gpu.model as gpu_model, gpu.vram_gb,
                        gpass.g3d_mark as gpu_g3d_mark,
                        cpass.passmark_score as cpu_passmark,
                        cr23.cinebench_r23_multi as cpu_r23_multi,
                        NULL as ram_id, NULL as ram_name, NULL as ram_speed, NULL as ram_capacity, NULL as ram_type,
                        NULL as ssd_id, NULL as ssd_brand, NULL as ssd_model, NULL as ssd_capacity,
                        cl.ram_match_method, cl.ssd_match_method
                        {mb_select}
                        {monitor_select}
                    FROM computer_listings cl
                    LEFT JOIN cpu_reference cpu ON cl.matched_cpu_id = cpu.id
                    LEFT JOIN gpu_reference gpu ON cl.matched_gpu_id = gpu.id
                    LEFT JOIN gpu_reference_passmark gpass ON gpu.id = gpass.gpu_reference_id
                    LEFT JOIN cpu_benchmarks_passmark cpass ON cpu.normalized_name = cpass.cpu_name
                    LEFT JOIN cpu_benchmarks_r23 cr23 ON cpu.normalized_name = cr23.cpu_name
                    {mb_join}
                    {monitor_join}
                    WHERE cl.listing_id = %s
                """.format(mb_select=mb_select, mb_join=mb_join, monitor_select=monitor_select, monitor_join=monitor_join)

            cursor.execute(query, (listing_id,))

            row = cursor.fetchone()
            if not row:
                cursor.close()
                return jsonify({'success': False, 'error': 'Listing not found'}), 404

            listing = dict(row)

            # Convert Decimal to float
            if listing.get('price_eur') is not None:
                listing['price_eur'] = float(listing['price_eur'])
            if listing.get('vram_gb') is not None:
                listing['vram_gb'] = format_vram(listing['vram_gb'])

            # Compute benchmark-based scores
            # Fallback: when matched_ram_id / matched_ssd_id is NULL the JOIN
            # returns NULL for capacity — the data is actually in
            # cl.ram_match_method / cl.ssd_match_method (e.g. "fallback_ddr3_12gb",
            # "fallback_240gb_ssd"). parse it so the score doesn't read 0.
            if not listing.get('matched_ram_id') and listing.get('ram_match_method'):
                ram_m = re.search(r'(\d+)\s*gb', listing['ram_match_method'], re.IGNORECASE)
                if ram_m:
                    listing['ram_capacity'] = int(ram_m.group(1))
                # "ddr3"/"ddr4"/"ddr5" tokens in the method string
                ram_type_m = re.search(r'ddr[345]', listing['ram_match_method'], re.IGNORECASE)
                if ram_type_m and not listing.get('ram_type'):
                    listing['ram_type'] = ram_type_m.group(0).upper()
            if not listing.get('matched_ssd_id') and listing.get('ssd_match_method'):
                ssd_m = re.search(r'(\d+)\s*gb', listing['ssd_match_method'], re.IGNORECASE)
                if ssd_m:
                    listing['ssd_capacity'] = int(ssd_m.group(1))
            perf, value = compute_scores(listing)
            listing['performance_score'] = perf
            listing['value_score'] = value

            # Respect persisted build_type; fall back to title keyword detection only when not set
            if not listing.get('build_type'):
                title_lower = (listing.get('title') or '').lower()
                prebuilt_keywords = ['prebuilt', 'pre-built', 'complete', 'ready to use', 'gaming pc', 'desktop pc', 'assembled pc', 'build pc']
                listing['is_prebuilt'] = any(kw in title_lower for kw in prebuilt_keywords)
                listing['build_type'] = 'prebuilt' if listing['is_prebuilt'] else 'custom'
            else:
                listing['is_prebuilt'] = bool(listing.get('is_prebuilt'))

            # Build a simple breakdown
            breakdown = {
                'listing_id': listing['listing_id'],
                'title': listing['title'],
                'price_eur': listing['price_eur'] if listing.get('price_eur') else 0,
            }

            # Add CPU to breakdown if exists
            if listing.get('cpu_id'):
                # Get actual average price from listings table for this CPU model
                cursor.execute("""
                    SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                           MIN(l.price_eur) as min_price,
                           MAX(l.price_eur) as max_price,
                           COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'cpu'
                        AND l.is_active = true
                        AND l.matched_cpu_id = %s
                """, (listing['cpu_id'],))
                cpu_price_data = cursor.fetchone()

                if cpu_price_data and cpu_price_data['avg_price']:
                    cpu_avg = float(cpu_price_data['avg_price'])
                else:
                    # T160: fall back to all-time historical average, then a very low default
                    cursor.execute("""
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                               COUNT(*) as listing_count
                        FROM listings l
                        WHERE l.category = 'cpu'
                            AND l.matched_cpu_id = %s
                    """, (listing['cpu_id'],))
                    hist = cursor.fetchone()
                    cpu_avg = float(hist['avg_price']) if hist and hist['avg_price'] else 5.0

                breakdown['cpu'] = {
                    'producer': listing['cpu_producer'],
                    'name': listing['cpu_name'],
                    'model': listing['cpu_name'],
                    'socket': listing.get('cpu_socket') or listing.get('mb_socket'),
                }
                breakdown['cpu_avg_price'] = cpu_avg

            # Add GPU to breakdown if exists
            if listing.get('gpu_id'):
                # Get actual average price from listings table for this GPU model
                cursor.execute("""
                    SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                           MIN(l.price_eur) as min_price,
                           MAX(l.price_eur) as max_price,
                           COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'gpu'
                        AND l.is_active = true
                        AND l.matched_gpu_id = %s
                """, (listing['gpu_id'],))
                gpu_price_data = cursor.fetchone()

                if gpu_price_data and gpu_price_data['avg_price']:
                    gpu_avg = float(gpu_price_data['avg_price'])
                else:
                    # T160: fall back to all-time historical average, then MSRP*0.85
                    cursor.execute("""
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                               COUNT(*) as listing_count
                        FROM listings l
                        WHERE l.category = 'gpu'
                            AND l.matched_gpu_id = %s
                    """, (listing['gpu_id'],))
                    hist = cursor.fetchone()
                    if hist and hist['avg_price']:
                        gpu_avg = float(hist['avg_price'])
                    else:
                        cursor.execute("SELECT msrp_usd FROM gpu_reference WHERE id = %s", (listing['gpu_id'],))
                        msrp_row = cursor.fetchone()
                        gpu_avg = round(float(msrp_row['msrp_usd']) * 0.85, 2) if msrp_row and msrp_row['msrp_usd'] else 50.0

                breakdown['gpu'] = {
                    'vendor': listing['gpu_vendor'],
                    'model': listing['gpu_model'],
                    'vram_gb': listing['vram_gb']
                }
                breakdown['gpu_avg_price'] = gpu_avg

            # Add RAM to breakdown if exists (matched or fallback)
            ram_id = listing.get('ram_id')
            ram_capacity = listing.get('ram_capacity')
            ram_name = listing.get('ram_name')
            ram_speed = listing.get('ram_speed')
            ram_match_method = listing.get('ram_match_method', '')
            ram_type = None

            # Parse capacity from ram_match_method if no matched RAM data
            if not ram_capacity and ram_match_method:
                # Parse capacity from match method string like "16GB_DDR4" or "fallback_16GB"
                capacity_match = re.search(r'(\d+)\s*GB', ram_match_method, re.IGNORECASE)
                if capacity_match:
                    ram_capacity = int(capacity_match.group(1))
                # Parse DDR type
                ddr_match = re.search(r'DDR(\d+)', ram_match_method, re.IGNORECASE)
                if ddr_match:
                    ram_type = f"DDR{ddr_match.group(1)}"

            # Check if we have any RAM data (matched or fallback detected)
            if ram_id or ram_match_method:
                # Get actual average price from listings table for this RAM model
                if ram_id:
                    # Use outlier-filtered average (10th-90th percentile) for matched RAM models,
                    # so a single extreme listing doesn't distort the component price.
                    cursor.execute("""
                        WITH price_stats AS (
                            SELECT
                                PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY l.price_eur) as p10,
                                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY l.price_eur) as p90
                            FROM listings l
                            LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                            WHERE l.category = 'ram'
                                AND l.is_active = true
                                AND fl.listing_id IS NULL
                                AND l.matched_ram_id = %s
                        )
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                               MIN(l.price_eur) as min_price,
                               MAX(l.price_eur) as max_price,
                               COUNT(*) as listing_count
                        FROM listings l
                        JOIN price_stats ps ON l.price_eur BETWEEN ps.p10 AND ps.p90
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ram'
                            AND l.is_active = true
                            AND fl.listing_id IS NULL
                            AND l.matched_ram_id = %s
                    """, (ram_id, ram_id))
                    ram_price_data = cursor.fetchone()
                    if ram_price_data and ram_price_data.get('avg_price'):
                        ram_avg = float(ram_price_data['avg_price'])
                    else:
                        # Active listing gone; fallback to historical (inactive) listings for this RAM model.
                        # For consistency, also exclude flagged listings from the historical average.
                        cursor.execute("""
                            SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                                   MIN(l.price_eur) as min_price,
                                   MAX(l.price_eur) as max_price,
                                   COUNT(*) as listing_count
                            FROM listings l
                            LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                            WHERE l.category = 'ram'
                                AND fl.listing_id IS NULL
                                AND l.matched_ram_id = %s
                        """, (ram_id,))
                        ram_price_data = cursor.fetchone()
                        ram_avg = float(ram_price_data['avg_price']) if ram_price_data and ram_price_data.get('avg_price') else 50.0
                        if ram_avg == 50.0:
                            # T160 safeguard: when historical fallback is also empty (0 active + 0 historical),
                            # keep the raw 50.0 default as before.
                            pass
                else:
                    # Fallback detected RAM - query actual market data for generic RAM
                    # For generic RAM, query ALL active RAM listings with matching capacity
                    # We match both by ram_reference.capacity_gb AND by title
                    if ram_capacity:
                        # Query ONLY matched RAM listings by capacity and DDR type
                        # DEBUG: Get list of listings used for calculation
                        debug_query = """
                            SELECT l.listing_id, l.title, l.price_eur, l.is_active,
                                   r.name as ram_name, r.capacity_gb as ref_capacity, r.type as ddr_type
                            FROM listings l
                            JOIN ram_reference r ON l.matched_ram_id = r.id
                            LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                            WHERE l.category = 'ram'
                                AND l.is_active = true
                                AND fl.listing_id IS NULL
                                AND r.capacity_gb = %s
                                AND r.type = %s
                            ORDER BY l.price_eur
                        """

                        generic_ram_query = """
                            SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                                   MIN(l.price_eur) as min_price,
                                   MAX(l.price_eur) as max_price,
                                   COUNT(*) as listing_count
                            FROM listings l
                            JOIN ram_reference r ON l.matched_ram_id = r.id
                            LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                            WHERE l.category = 'ram'
                                AND l.is_active = true
                                AND fl.listing_id IS NULL
                                AND r.capacity_gb = %s
                                AND r.type = %s
                        """

                        title_capacity_pattern = f"%{ram_capacity}GB%"
                        ddr_type_value = ram_type or 'DDR4'

                        # Debug queries removed; generic RAM price is computed from active RAM listings.
                        cursor.execute(debug_query, (ram_capacity, ddr_type_value))
                        ddr_listings = cursor.fetchall()

                        # If NO results with DDR filter, query without DDR type (but only if zero results)
                        if len(ddr_listings) == 0:
                            # Use capacity-only query but with outlier filtering
                            # Filter out listings below 10th percentile (likely errors) and above 90th percentile
                            generic_ram_query_no_ddr = """WITH price_stats AS (SELECT PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY l.price_eur) as p10, PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY l.price_eur) as p90 FROM listings l JOIN ram_reference r ON l.matched_ram_id = r.id LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id WHERE l.category = 'ram' AND l.is_active = true AND fl.listing_id IS NULL AND r.capacity_gb = %s) SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price, MIN(l.price_eur) as min_price, MAX(l.price_eur) as max_price, COUNT(*) as listing_count FROM listings l JOIN ram_reference r ON l.matched_ram_id = r.id LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id CROSS JOIN price_stats ps WHERE l.category = 'ram' AND l.is_active = true AND fl.listing_id IS NULL AND r.capacity_gb = %s AND l.price_eur >= ps.p10 * 0.5 AND l.price_eur <= ps.p90 * 1.5"""
                            cursor.execute(generic_ram_query_no_ddr, (ram_capacity, ram_capacity))
                            all_listings_data = cursor.fetchone()

                            generic_price_data = all_listings_data
                        else:
                            cursor.execute(generic_ram_query, (ram_capacity, ddr_type_value))
                            generic_price_data = cursor.fetchone()

                        if generic_price_data and generic_price_data.get('avg_price'):
                            ram_avg = float(generic_price_data['avg_price'])
                        else:
                            # Ultimate fallback - use a slightly higher default based on capacity
                            capacity_fallbacks = {4: 25.0, 8: 35.0, 16: 65.0, 32: 120.0, 64: 250.0}
                            ram_avg = capacity_fallbacks.get(ram_capacity, 50.0)
                    else:
                        ram_avg = 50.0

                # Build display name
                if ram_name:
                    display_name = ram_name
                elif ram_capacity:
                    display_name = f"Generic {ram_capacity}GB {ram_type or 'DDR4'}"
                else:
                    display_name = "RAM (detected)"

                # Add fallback indicator only for real fallback tokens (not raw 'fallback_ddr4_16gb')
                if not ram_id and ram_match_method and not ram_match_method.startswith('fallback_'):
                    display_name += f" ({ram_match_method})"

                breakdown['ram'] = {
                    'ram_id': ram_id,
                    'name': display_name,
                    'capacity_gb': ram_capacity,
                    'speed': ram_speed,
                    'ram_type': ram_type,
                    'match_method': ram_match_method,
                    'is_matched': bool(ram_id)
                }
                breakdown['ram_avg_price'] = ram_avg

            # Add SSD to breakdown if exists (matched or fallback)
            ssd_id = listing.get('ssd_id')
            ssd_brand = listing.get('ssd_brand')
            ssd_model = listing.get('ssd_model')
            ssd_capacity = listing.get('ssd_capacity')
            ssd_match_method = listing.get('ssd_match_method', '')

            # Parse capacity from ssd_match_method if no matched SSD data
            if not ssd_capacity and ssd_match_method:
                # Parse capacity from match method string like "512GB_SSD" or "fallback_512GB"
                capacity_match = re.search(r'(\d+)\s*GB', ssd_match_method, re.IGNORECASE)
                if capacity_match:
                    ssd_capacity = int(capacity_match.group(1))

            # Only include SSD in breakdown if we have actual data (matched, capacity, or meaningful detection)
            ssd_method_useful = bool(ssd_match_method and ssd_match_method.strip().lower() not in ('none', '', 'null'))
            if ssd_id or ssd_capacity or ssd_method_useful:
                # Get actual average price from listings table for this SSD model
                if ssd_id:
                    cursor.execute("""
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                               MIN(l.price_eur) as min_price,
                               MAX(l.price_eur) as max_price,
                               COUNT(*) as listing_count
                        FROM listings l
                        WHERE l.category = 'ssd'
                            AND l.is_active = true
                            AND l.matched_ssd_id = %s
                    """, (ssd_id,))
                    ssd_price_data = cursor.fetchone()

                    # If matched SSD query returns no results (reference record missing),
                    # fall back to capacity-based pricing
                    if ssd_price_data and ssd_price_data.get('avg_price'):
                        ssd_avg = float(ssd_price_data['avg_price'])
                    elif ssd_capacity:
                        # Matched but no reference record - query by capacity range
                        # For 480-512GB SSDs, query all SSDs in that range
                        if 480 <= ssd_capacity <= 512:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND (l.title ILIKE %s OR l.title ILIKE %s OR l.title ILIKE %s)
                            """, ('%480GB%', '%500GB%', '%512GB%'))
                            capacity_price_data = cursor.fetchone()
                            ssd_avg = float(capacity_price_data['avg_price']) if capacity_price_data and capacity_price_data.get('avg_price') else 72.0
                        # For 1.9-2TB SSDs (1900-2048GB)
                        elif 1900 <= ssd_capacity <= 2048:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND (l.title ILIKE %s OR l.title ILIKE %s OR l.title ILIKE %s)
                            """, ('%1900GB%', '%2000GB%', '%2048GB%'))
                            capacity_price_data = cursor.fetchone()
                            ssd_avg = float(capacity_price_data['avg_price']) if capacity_price_data and capacity_price_data.get('avg_price') else 218.0
                        else:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND l.title ILIKE %s
                            """, (f"%{ssd_capacity}GB%",))
                            capacity_price_data = cursor.fetchone()
                            ssd_avg = float(capacity_price_data['avg_price']) if capacity_price_data and capacity_price_data.get('avg_price') else 72.0
                    else:
                        ssd_avg = 72.0  # Default for 480-512GB SSD
                else:
                    # Fallback detected SSD - query generic pricing by capacity
                    if ssd_capacity:
                        # For 480-512GB SSDs, query all SSDs in that range
                        if 480 <= ssd_capacity <= 512:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND (l.title ILIKE %s OR l.title ILIKE %s OR l.title ILIKE %s)
                            """, ('%480GB%', '%500GB%', '%512GB%'))
                            ssd_price_data = cursor.fetchone()
                            ssd_avg = float(ssd_price_data['avg_price']) if ssd_price_data and ssd_price_data['avg_price'] else 72.0
                        # For 1.9-2TB SSDs (1900-2048GB)
                        elif 1900 <= ssd_capacity <= 2048:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND (l.title ILIKE %s OR l.title ILIKE %s OR l.title ILIKE %s)
                            """, ('%1900GB%', '%2000GB%', '%2048GB%'))
                            ssd_price_data = cursor.fetchone()
                            ssd_avg = float(ssd_price_data['avg_price']) if ssd_price_data and ssd_price_data['avg_price'] else 218.0
                        else:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                                WHERE l.category = 'ssd'
                                    AND l.is_active = true
                                    AND fl.listing_id IS NULL
                                    AND l.title ILIKE %s
                            """, (f"%{ssd_capacity}GB%",))
                            ssd_price_data = cursor.fetchone()
                            ssd_avg = float(ssd_price_data['avg_price']) if ssd_price_data and ssd_price_data['avg_price'] else 72.0
                    else:
                        ssd_avg = 72.0

                # Build display name
                if ssd_brand and ssd_model:
                    display_name = f"{ssd_brand} {ssd_model}"
                elif ssd_capacity:
                    display_name = f"Generic {ssd_capacity}GB SSD"
                elif ssd_match_method and ssd_match_method.lower() != 'none':
                    display_name = "SSD (detected)"
                else:
                    display_name = "No SSD detected"

                breakdown['ssd'] = {
                    'name': display_name,
                    'brand': ssd_brand,
                    'model': ssd_model,
                    'capacity_gb': ssd_capacity,
                    'match_method': ssd_match_method,
                    'is_matched': bool(ssd_id)
                }
                breakdown['ssd_avg_price'] = ssd_avg

            # Add MOTHERBOARD detection for generic/fallback cases
            # Check if we have CPU data but no specific motherboard match
            cpu_socket = None
            cpu_chipsets = []
            if listing.get('cpu_id') and listing.get('cpu_name'):
                # Extract socket from cpu_name (e.g., "Intel Core i5-6500 (LGA 1151)")
                cpu_name = listing.get('cpu_name', '')
                socket_match = re.search(r'\(([A-Z0-9\s]+)\)', cpu_name)
                if socket_match:
                    cpu_socket = socket_match.group(1).strip()
                # Normalize socket name
                socket_key = None
                for alias, standard in SOCKET_ALIASES.items():
                    if alias.upper() in cpu_name.upper() or (cpu_socket and alias.upper() in cpu_socket.upper()):
                        socket_key = standard
                        break
                if not socket_key and cpu_socket:
                    for standard in SOCKET_CHIPSETS.keys():
                        if standard.upper() in cpu_socket.upper():
                            socket_key = standard
                            break
                if socket_key:
                    cpu_chipsets = SOCKET_CHIPSETS.get(socket_key, [])

            # Add motherboard to breakdown
            motherboard_id = listing.get('motherboard_id')
            motherboard_match_method = listing.get('motherboard_match_method', '')
            mb_avg = 80.0

            if motherboard_id:
                # Matched motherboard - use actual reference data
                mb_brand = listing.get('mb_brand')
                mb_model = listing.get('mb_model')
                mb_socket = listing.get('mb_socket')
                mb_chipset = listing.get('mb_chipset')
                motherboard_name = f"{mb_brand} {mb_model}".strip() if (mb_brand or mb_model) else f"Motherboard (ID {motherboard_id})"

                # Get average price from motherboard listings
                cursor.execute("""
                    SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                           MIN(l.price_eur) as min_price,
                           MAX(l.price_eur) as max_price,
                           COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'motherboard'
                        AND l.is_active = true
                        AND l.motherboard_model_id = %s
                """, (motherboard_id,))
                mb_price_data = cursor.fetchone()
                if mb_price_data and mb_price_data.get('avg_price'):
                    mb_avg = float(mb_price_data['avg_price'])

                breakdown['motherboard'] = {
                    'motherboard_id': motherboard_id,
                    'name': motherboard_name,
                    'brand': mb_brand,
                    'model': mb_model,
                    'socket': mb_socket,
                    'chipset': mb_chipset,
                    'is_generic': False,
                    'match_method': motherboard_match_method,
                    'is_matched': True
                }
            elif listing.get('cpu_id'):
                # Generic motherboard detected based on CPU
                cpu_socket = None
                cpu_chipsets = []
                if listing.get('cpu_name'):
                    cpu_name = listing.get('cpu_name', '')
                    socket_match = re.search(r'\(([A-Z0-9\s]+)\)', cpu_name)
                    if socket_match:
                        cpu_socket = socket_match.group(1).strip()
                    socket_key = None
                    for alias, standard in SOCKET_ALIASES.items():
                        if alias.upper() in cpu_name.upper() or (cpu_socket and alias.upper() in cpu_socket.upper()):
                            socket_key = standard
                            break
                    if not socket_key and cpu_socket:
                        for standard in SOCKET_CHIPSETS.keys():
                            if standard.upper() in cpu_socket.upper():
                                socket_key = standard
                                break
                    if socket_key:
                        cpu_chipsets = SOCKET_CHIPSETS.get(socket_key, [])

                if cpu_chipsets:
                    motherboard_name = f"Generic {socket_key} Motherboard (supports {', '.join(cpu_chipsets[:3])}...)"
                else:
                    motherboard_name = f"Generic Motherboard for {listing.get('cpu_name', 'CPU')}"

                if cpu_chipsets:
                    if mb_table_exists:
                        try:
                            cursor.execute("""
                                SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                                FROM listings l
                                LEFT JOIN motherboard_models mb ON l.matched_motherboard_id = mb.id
                                WHERE l.category = 'motherboard'
                                    AND l.is_active = true
                                    AND (mb.chipset = ANY(%s) OR l.title ILIKE ANY(%s))
                            """, (cpu_chipsets, [f'%{c}%' for c in cpu_chipsets]))
                            mb_price_data = cursor.fetchone()
                            if mb_price_data and mb_price_data.get('avg_price'):
                                mb_avg = float(mb_price_data['avg_price'])
                        except:
                            pass

                    if mb_avg == 80.0:
                        cursor.execute("""
                            SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                            FROM listings l
                            WHERE l.category = 'motherboard' AND l.is_active = true
                        """)
                        mb_fallback = cursor.fetchone()
                        if mb_fallback and mb_fallback.get('avg_price'):
                            mb_avg = float(mb_fallback['avg_price'])

                breakdown['motherboard'] = {
                    'name': motherboard_name,
                    'socket': socket_key or cpu_socket,
                    'supported_chipsets': cpu_chipsets,
                    'is_generic': True,
                    'match_method': 'generic_fallback',
                    'is_matched': False
                }

            if 'motherboard' in breakdown:
                breakdown['motherboard_avg_price'] = mb_avg

            # Add MONITOR to breakdown if matched (Bug 13 fix — the popup used to show
            # only CPU/GPU/RAM/SSD/Motherboard and never loaded matched_monitor_id,
            # so monitors like the Samsung B2030N in listing 'lpief' were invisible
            # and the price-analysis was missing ~€100 of component value).
            monitor_id = listing.get('mon_id')
            monitor_match_method = listing.get('monitor_match_method', '')
            monitor_included = listing.get('monitor_included', False)
            mon_avg = 0.0

            if monitor_id and monitor_included:
                mon_brand = listing.get('mon_brand')
                mon_model = listing.get('mon_model')
                mon_size = listing.get('mon_size')
                mon_resolution = listing.get('mon_resolution')
                mon_refresh_rate = listing.get('mon_refresh_rate')
                mon_panel_type = listing.get('mon_panel_type')
                monitor_name = f"{mon_brand} {mon_model}".strip() if (mon_brand or mon_model) else f"Monitor (ID {monitor_id})"

                # Try to get the average price from the monitor listings table
                cursor.execute("""
                    SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                           MIN(l.price_eur) as min_price,
                           MAX(l.price_eur) as max_price,
                           COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'monitor'
                        AND l.is_active = true
                        AND l.monitor_model_id = %s
                """, (monitor_id,))
                mon_price_data = cursor.fetchone()
                if mon_price_data and mon_price_data.get('avg_price'):
                    mon_avg = float(mon_price_data['avg_price'])
                else:
                    # Historical fallback (inactive listings)
                    cursor.execute("""
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                        FROM listings l
                        WHERE l.category = 'monitor' AND l.monitor_model_id = %s
                    """, (monitor_id,))
                    hist = cursor.fetchone()
                    if hist and hist.get('avg_price'):
                        mon_avg = float(hist['avg_price'])
                    else:
                        # Last-resort fallback: use the listing's stored fallback_monitor_price,
                        # which the scraper writes when no real listing price is available
                        fallback = listing.get('fallback_monitor_price')
                        mon_avg = float(fallback) if fallback is not None else 100.0

                breakdown['monitor'] = {
                    'monitor_id': monitor_id,
                    'name': monitor_name,
                    'brand': mon_brand,
                    'model': mon_model,
                    'size': mon_size,
                    'resolution': mon_resolution,
                    'refresh_rate': mon_refresh_rate,
                    'panel_type': mon_panel_type,
                    'is_matched': True,
                    'is_included': True,
                    'match_method': monitor_match_method
                }
                breakdown['monitor_avg_price'] = mon_avg

            # Compute live grand totals from average prices so the price-analysis
            # widget always reflects current market data, not stale stored totals.
            detected_total = sum(
                breakdown.get(f'{comp}_avg_price', 0) or 0
                for comp in ['cpu', 'gpu', 'ram', 'ssd', 'motherboard', 'psu', 'case', 'monitor']
                if comp in breakdown
            )
            breakdown['detected_total'] = round(detected_total, 2)
            breakdown['fallback_total'] = 0.0
            breakdown['grand_total'] = round(detected_total, 2)

            cursor.close()

            return jsonify({
                'success': True,
                'listing': listing,
                'breakdown': breakdown
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/stats')
@cache_control(max_age=30)
def get_computer_stats():
    """Get computer statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if computer_listings table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'computer_listings'
                )
            """)
            table_exists = cursor.fetchone()['exists']

            if not table_exists:
                cursor.close()
                return jsonify({
                    'success': True,
                    'stats': {
                        'total': 0,
                        'active': 0,
                        'avg_price': 0,
                        'avg_components_total': 0,
                        'avg_listing_vs_components': 0,
                        'with_cpu': 0,
                        'with_gpu': 0
                    }
                })

            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM computer_listings")
            total = cursor.fetchone()['total']

            # Get active count
            cursor.execute("SELECT COUNT(*) as active FROM computer_listings WHERE is_active = true")
            active = cursor.fetchone()['active']

            # Get average price
            cursor.execute("SELECT ROUND(AVG(cl.price_eur)::numeric, 2) as avg_price FROM computer_listings cl WHERE cl.is_active = true")
            avg_price = cursor.fetchone()['avg_price'] or 0

            # Get count with CPU
            cursor.execute("SELECT COUNT(*) as with_cpu FROM computer_listings WHERE matched_cpu_id IS NOT NULL AND is_active = true")
            with_cpu = cursor.fetchone()['with_cpu']

            # Get count with GPU
            cursor.execute("SELECT COUNT(*) as with_gpu FROM computer_listings WHERE matched_gpu_id IS NOT NULL AND is_active = true")
            with_gpu = cursor.fetchone()['with_gpu']

            # New dashboard card: avg sum of component prices per active listing
            # + avg listing-vs-components delta. components_total_eur is the
            # backend-computed sum of CPU/GPU/RAM/SSD/MB/PSU/Case/monitor
            # prices for the listing (NULL when no components detected).
            cursor.execute("""
                SELECT
                    ROUND(AVG(components_total_eur)::numeric, 0) as avg_components_total,
                    ROUND(AVG(CASE
                        WHEN components_total_eur IS NOT NULL AND price_eur IS NOT NULL
                        THEN price_eur - components_total_eur
                        ELSE NULL
                    END)::numeric, 0) as avg_listing_vs_components,
                    COUNT(*) FILTER (WHERE components_total_eur IS NOT NULL) as component_count
                FROM computer_listings
                WHERE is_active = true
            """)
            comp_stats = cursor.fetchone() or {}
            avg_components_total = float(comp_stats.get('avg_components_total') or 0)
            avg_listing_vs_components = float(comp_stats.get('avg_listing_vs_components') or 0)
            component_count = int(comp_stats.get('component_count') or 0)

            cursor.close()

            # Convert Decimal to float
            if hasattr(avg_price, '__float__'):
                avg_price = float(avg_price)

            return jsonify({
                'success': True,
                'stats': {
                    'total': total,
                    'active': active,
                    'avg_price': avg_price,
                    'avg_components_total': avg_components_total,
                    'avg_listing_vs_components': avg_listing_vs_components,
                    'component_count': component_count,
                    'with_cpu': with_cpu,
                    'with_gpu': with_gpu
                }
            })
        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update-listing-type', methods=['POST'])
def update_listing_type():
    """Persist build_type/prebuilt flag for a computer listing."""
    data = request.get_json() or {}
    listing_id = data.get('listing_id')
    build_type = data.get('build_type', 'custom')

    if not listing_id:
        return jsonify({'success': False, 'error': 'listing_id required'}), 400

    if build_type not in ('custom', 'prebuilt', 'office'):
        return jsonify({'success': False, 'error': 'Invalid build_type'}), 400

    is_prebuilt = build_type == 'prebuilt'

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE computer_listings
                SET build_type = %s, is_prebuilt = %s, updated_at = NOW()
                WHERE listing_id = %s
            """, (build_type, is_prebuilt, listing_id))
            conn.commit()
            cursor.close()
            return jsonify({'success': True, 'build_type': build_type, 'is_prebuilt': is_prebuilt})
        except Exception as e:
            conn.rollback()
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unmark-prebuilt', methods=['POST'])
def unmark_prebuilt():
    """Clear prebuilt flag and reset build_type to custom."""
    data = request.get_json() or {}
    listing_id = data.get('listing_id')
    if not listing_id:
        return jsonify({'success': False, 'error': 'listing_id required'}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE computer_listings
                SET build_type = 'custom', is_prebuilt = false, updated_at = NOW()
                WHERE listing_id = %s
            """, (listing_id,))
            conn.commit()
            cursor.close()
            return jsonify({'success': True, 'build_type': 'custom', 'is_prebuilt': False})
        except Exception as e:
            conn.rollback()
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gpu-compare')
def gpu_compare_page():
    """GPU comparison page."""
    return render_template('gpu_compare.html')


@app.route('/gpu')
def gpu_page():
    """GPU listings page."""
    return render_template('gpu.html')


# === GPU palette variants (same /gpu structure, different colors) ===
PALETTES = {
    1: {
        'name': 'Indigo',
        'style': '''
:root {
  --c-bg:#0f1120; --c-surface:#1a1a2e; --c-surface-2:#232342; --c-surface-3:#2a2a4a;
  --c-border:#3a3a5a; --c-text:#e0e0e0; --c-text-dim:#a0a0b0; --c-text-mute:#888;
  --c-accent:#667eea; --c-accent-2:#764ba2;
  --c-accent-glow:rgba(102,126,234,.35); --c-accent-bg:rgba(102,126,234,.12);
  --c-accent-border:rgba(102,126,234,.4);
  --c-success:#16a34a; --c-warning:#f59e0b; --c-danger:#e74c3c;
  --c-nvidia:#76b900; --c-amd:#ed1c24; --c-intel:#0071c5;
}
''',
    },
    2: {
        'name': 'Aurora',
        'style': '''
:root {
  --c-bg:#061a14; --c-surface:#0d2620; --c-surface-2:#143b32; --c-surface-3:#1b4d42;
  --c-border:#28594d; --c-text:#e6f7f1; --c-text-dim:#9ec9b7; --c-text-mute:#5e9986;
  --c-accent:#10e0a0; --c-accent-2:#22d3ee;
  --c-accent-glow:rgba(16,224,160,.4); --c-accent-bg:rgba(16,224,160,.14);
  --c-accent-border:rgba(16,224,160,.45);
  --c-success:#34d399; --c-warning:#fbbf24; --c-danger:#f87171;
  --c-nvidia:#a3e635; --c-amd:#fb7185; --c-intel:#67e8f9;
}
''',
    },
    3: {
        'name': 'Sunset',
        'style': '''
:root {
  --c-bg:#1c1009; --c-surface:#2a1810; --c-surface-2:#3a2418; --c-surface-3:#4a2e20;
  --c-border:#5a3a28; --c-text:#fdf2e3; --c-text-dim:#d4b896; --c-text-mute:#8a6a4a;
  --c-accent:#f59e0b; --c-accent-2:#ef4444;
  --c-accent-glow:rgba(245,158,11,.4); --c-accent-bg:rgba(245,158,11,.14);
  --c-accent-border:rgba(245,158,11,.45);
  --c-success:#84cc16; --c-warning:#fb923c; --c-danger:#dc2626;
  --c-nvidia:#bef264; --c-amd:#fca5a5; --c-intel:#7dd3fc;
}
''',
    },
    4: {
        'name': 'Midnight',
        'style': '''
:root {
  --c-bg:#0d0820; --c-surface:#181233; --c-surface-2:#241a45; --c-surface-3:#322358;
  --c-border:#3f2c6a; --c-text:#f0e9ff; --c-text-dim:#b5a5e0; --c-text-mute:#7a6aa0;
  --c-accent:#a855f7; --c-accent-2:#ec4899;
  --c-accent-glow:rgba(168,85,247,.4); --c-accent-bg:rgba(168,85,247,.14);
  --c-accent-border:rgba(168,85,247,.45);
  --c-success:#22c55e; --c-warning:#fbbf24; --c-danger:#ef4444;
  --c-nvidia:#d9f99d; --c-amd:#fda4af; --c-intel:#a5b4fc;
}
''',
    },
    5: {
        'name': 'Frost',
        'style': '''
:root {
  --c-bg:#f1f5f9; --c-surface:#ffffff; --c-surface-2:#f8fafc; --c-surface-3:#e2e8f0;
  --c-border:#cbd5e1; --c-text:#0f172a; --c-text-dim:#475569; --c-text-mute:#94a3b8;
  --c-accent:#6366f1; --c-accent-2:#8b5cf6;
  --c-accent-glow:rgba(99,102,241,.25); --c-accent-bg:rgba(99,102,241,.1);
  --c-accent-border:rgba(99,102,241,.3);
  --c-success:#059669; --c-warning:#d97706; --c-danger:#dc2626;
  --c-nvidia:#4d7c0f; --c-amd:#b91c1c; --c-intel:#1d4ed8;
}
''',
    },
}


def _render_palette(palette_id):
    p = PALETTES[palette_id]
    return render_template(
        'gpu_palette_base.html',
        palette_id=palette_id,
        palette_name=p['name'],
        palette_style=p['style'],
    )


@app.route('/gpu-palette1')
def gpu_palette1_page():
    return _render_palette(1)


@app.route('/gpu-palette2')
def gpu_palette2_page():
    return _render_palette(2)


@app.route('/gpu-palette3')
def gpu_palette3_page():
    return _render_palette(3)


@app.route('/gpu-palette4')
def gpu_palette4_page():
    return _render_palette(4)


@app.route('/gpu-palette5')
def gpu_palette5_page():
    return _render_palette(5)


# === Subtle palette variants (palette 6-10) ===
PALETTES.update({
    6: {
        'name': 'Slate',
        'style': '''
:root {
  --c-bg:#0f172a; --c-surface:#1e293b; --c-surface-2:#334155; --c-surface-3:#475569;
  --c-border:#64748b; --c-text:#f1f5f9; --c-text-dim:#94a3b8; --c-text-mute:#64748b;
  --c-accent:#60a5fa; --c-accent-2:#7dd3fc;
  --c-accent-glow:rgba(96,165,250,.25); --c-accent-bg:rgba(96,165,250,.1);
  --c-accent-border:rgba(96,165,250,.3);
  --c-success:#4ade80; --c-warning:#fbbf24; --c-danger:#f87171;
  --c-nvidia:#a3e635; --c-amd:#fb7185; --c-intel:#7dd3fc;
}
''',
    },
    7: {
        'name': 'Stone',
        'style': '''
:root {
  --c-bg:#1c1917; --c-surface:#292524; --c-surface-2:#44403c; --c-surface-3:#57534e;
  --c-border:#78716c; --c-text:#f5f5f4; --c-text-dim:#a8a29e; --c-text-mute:#78716c;
  --c-accent:#d6d3d1; --c-accent-2:#a8a29e;
  --c-accent-glow:rgba(214,211,209,.2); --c-accent-bg:rgba(214,211,209,.08);
  --c-accent-border:rgba(214,211,209,.25);
  --c-success:#86efac; --c-warning:#fcd34d; --c-danger:#fca5a5;
  --c-nvidia:#bef264; --c-amd:#fda4af; --c-intel:#93c5fd;
}
''',
    },
    8: {
        'name': 'Pearl',
        'style': '''
:root {
  --c-bg:#fafaf9; --c-surface:#ffffff; --c-surface-2:#f5f5f4; --c-surface-3:#e7e5e4;
  --c-border:#d6d3d1; --c-text:#1c1917; --c-text-dim:#57534e; --c-text-mute:#a8a29e;
  --c-accent:#78716c; --c-accent-2:#57534e;
  --c-accent-glow:rgba(120,113,108,.15); --c-accent-bg:rgba(120,113,108,.06);
  --c-accent-border:rgba(120,113,108,.2);
  --c-success:#16a34a; --c-warning:#d97706; --c-danger:#dc2626;
  --c-nvidia:#4d7c0f; --c-amd:#b91c1c; --c-intel:#1d4ed8;
}
''',
    },
    9: {
        'name': 'Graphite',
        'style': '''
:root {
  --c-bg:#0a0a0a; --c-surface:#171717; --c-surface-2:#262626; --c-surface-3:#404040;
  --c-border:#525252; --c-text:#fafafa; --c-text-dim:#a3a3a3; --c-text-mute:#737373;
  --c-accent:#14b8a6; --c-accent-2:#06b6d4;
  --c-accent-glow:rgba(20,184,166,.3); --c-accent-bg:rgba(20,184,166,.1);
  --c-accent-border:rgba(20,184,166,.35);
  --c-success:#4ade80; --c-warning:#fbbf24; --c-danger:#f87171;
  --c-nvidia:#a3e635; --c-amd:#fb7185; --c-intel:#67e8f9;
}
''',
    },
    10: {
        'name': 'Onyx',
        'style': '''
:root {
  --c-bg:#000000; --c-surface:#0a0a0a; --c-surface-2:#141414; --c-surface-3:#1f1f1f;
  --c-border:#2e2e2e; --c-text:#ededed; --c-text-dim:#9a9a9a; --c-text-mute:#5a5a5a;
  --c-accent:#c084fc; --c-accent-2:#a78bfa;
  --c-accent-glow:rgba(192,132,252,.3); --c-accent-bg:rgba(192,132,252,.1);
  --c-accent-border:rgba(192,132,252,.35);
  --c-success:#86efac; --c-warning:#fde047; --c-danger:#fca5a5;
  --c-nvidia:#bef264; --c-amd:#fda4af; --c-intel:#a5b4fc;
}
''',
    },
})


def _render_palette_subtle(palette_id):
    p = PALETTES[palette_id]
    return render_template(
        'gpu_palette_base.html',
        palette_id=palette_id,
        palette_name=p['name'],
        palette_style=p['style'],
    )


@app.route('/gpu-palette6')
def gpu_palette6_page():
    return _render_palette_subtle(6)


@app.route('/gpu-palette7')
def gpu_palette7_page():
    return _render_palette_subtle(7)


@app.route('/gpu-palette8')
def gpu_palette8_page():
    return _render_palette_subtle(8)


@app.route('/gpu-palette9')
def gpu_palette9_page():
    return _render_palette_subtle(9)


@app.route('/gpu-palette10')
def gpu_palette10_page():
    return _render_palette_subtle(10)


# === Personality palettes (11-20) — each one has a distinct mood ===
PALETTES.update({
    11: {
        'name': 'Sunshine',
        'style': '''
:root {
  --c-bg:#fffbeb; --c-surface:#ffffff; --c-surface-2:#fef3c7; --c-surface-3:#fde68a;
  --c-border:#fbbf24; --c-text:#1c1917; --c-text-dim:#78350f; --c-text-mute:#a16207;
  --c-accent:#f59e0b; --c-accent-2:#ea580c;
  --c-accent-glow:rgba(245,158,11,.35); --c-accent-bg:rgba(245,158,11,.12);
  --c-accent-border:rgba(245,158,11,.4);
  --c-success:#16a34a; --c-warning:#ca8a04; --c-danger:#dc2626;
  --c-nvidia:#15803d; --c-amd:#b91c1c; --c-intel:#1d4ed8;
}
body { background-image: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(251,191,36,.12) 0%, transparent 60%); }
''',
    },
    12: {
        'name': 'Warm Cream',
        'style': '''
:root {
  --c-bg:#f5ebd9; --c-surface:#fbf3e1; --c-surface-2:#ede0c4; --c-surface-3:#ddc99e;
  --c-border:#c8a47e; --c-text:#3a2412; --c-text-dim:#7c5635; --c-text-mute:#a8855a;
  --c-accent:#c2410c; --c-accent-2:#9a3412;
  --c-accent-glow:rgba(194,65,12,.25); --c-accent-bg:rgba(194,65,12,.1);
  --c-accent-border:rgba(194,65,12,.3);
  --c-success:#15803d; --c-warning:#a16207; --c-danger:#991b1b;
  --c-nvidia:#3f6212; --c-amd:#991b1b; --c-intel:#1e40af;
}
body { background-image: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(194,65,12,.08) 0%, transparent 60%); }
''',
    },
    13: {
        'name': 'Soft Pastel',
        'style': '''
:root {
  --c-bg:#fdf4f0; --c-surface:#ffffff; --c-surface-2:#fce7e0; --c-surface-3:#f8d4ca;
  --c-border:#f4c5b5; --c-text:#3d2c2a; --c-text-dim:#7c5a55; --c-text-mute:#b89a92;
  --c-accent:#f472b6; --c-accent-2:#a78bfa;
  --c-accent-glow:rgba(244,114,182,.25); --c-accent-bg:rgba(244,114,182,.1);
  --c-accent-border:rgba(244,114,182,.3);
  --c-success:#65a30d; --c-warning:#d97706; --c-danger:#dc2626;
  --c-nvidia:#3f6212; --c-amd:#9f1239; --c-intel:#1e3a8a;
}
body { background-image: radial-gradient(ellipse 70% 50% at 30% 0%, rgba(244,114,182,.12) 0%, transparent 60%), radial-gradient(ellipse 70% 50% at 70% 100%, rgba(167,139,250,.12) 0%, transparent 60%); }
''',
    },
    14: {
        'name': 'Cyber',
        'style': '''
:root {
  --c-bg:#0a0e27; --c-surface:#111640; --c-surface-2:#1a1f55; --c-surface-3:#252b6e;
  --c-border:#3b3f8a; --c-text:#ededff; --c-text-dim:#a5a8d4; --c-text-mute:#6b6fa8;
  --c-accent:#ff006e; --c-accent-2:#00f5ff;
  --c-accent-glow:rgba(255,0,110,.4); --c-accent-bg:rgba(255,0,110,.14);
  --c-accent-border:rgba(255,0,110,.4);
  --c-success:#00f5ff; --c-warning:#fde047; --c-danger:#ff006e;
  --c-nvidia:#00f5ff; --c-amd:#ff006e; --c-intel:#a78bfa;
}
body { background-image: linear-gradient(180deg, #0a0e27 0%, #1a0a3a 50%, #0a0e27 100%); }
''',
    },
    15: {
        'name': 'Deep Space',
        'style': '''
:root {
  --c-bg:#020617; --c-surface:#0f172a; --c-surface-2:#1e1b4b; --c-surface-3:#312e81;
  --c-border:#3730a3; --c-text:#e0e7ff; --c-text-dim:#a5b4fc; --c-text-mute:#6366f1;
  --c-accent:#8b5cf6; --c-accent-2:#ec4899;
  --c-accent-glow:rgba(139,92,246,.5); --c-accent-bg:rgba(139,92,246,.14);
  --c-accent-border:rgba(139,92,246,.4);
  --c-success:#34d399; --c-warning:#facc15; --c-danger:#fb7185;
  --c-nvidia:#a3e635; --c-amd:#fb7185; --c-intel:#67e8f9;
}
body { background-image: radial-gradient(ellipse 60% 40% at 30% 20%, rgba(139,92,246,.18) 0%, transparent 50%), radial-gradient(ellipse 50% 40% at 75% 80%, rgba(236,72,153,.15) 0%, transparent 50%), radial-gradient(ellipse 30% 30% at 90% 10%, rgba(56,189,248,.1) 0%, transparent 50%); }
body::before { content:''; position:fixed; inset:0; background-image: radial-gradient(1px 1px at 12% 18%, white, transparent), radial-gradient(1px 1px at 28% 65%, white, transparent), radial-gradient(1px 1px at 55% 12%, white, transparent), radial-gradient(1px 1px at 78% 48%, white, transparent), radial-gradient(1px 1px at 88% 82%, white, transparent), radial-gradient(1px 1px at 38% 88%, white, transparent), radial-gradient(1px 1px at 65% 32%, white, transparent), radial-gradient(1px 1px at 22% 42%, white, transparent); opacity: .6; pointer-events: none; }
''',
    },
    16: {
        'name': 'Forest',
        'style': '''
:root {
  --c-bg:#0d1f12; --c-surface:#14271a; --c-surface-2:#1d3523; --c-surface-3:#28472f;
  --c-border:#3a5d40; --c-text:#ecfccb; --c-text-dim:#bef264; --c-text-mute:#84cc16;
  --c-accent:#84cc16; --c-accent-2:#22c55e;
  --c-accent-glow:rgba(132,204,22,.35); --c-accent-bg:rgba(132,204,22,.12);
  --c-accent-border:rgba(132,204,22,.4);
  --c-success:#22c55e; --c-warning:#fbbf24; --c-danger:#ef4444;
  --c-nvidia:#bef264; --c-amd:#fb7185; --c-intel:#67e8f9;
}
body { background-image: radial-gradient(ellipse 70% 50% at 20% 0%, rgba(34,197,94,.12) 0%, transparent 60%), radial-gradient(ellipse 70% 50% at 80% 100%, rgba(132,204,22,.08) 0%, transparent 60%); }
''',
    },
    17: {
        'name': 'Amber Glow',
        'style': '''
:root {
  --c-bg:#0c0a09; --c-surface:#1c1917; --c-surface-2:#292524; --c-surface-3:#44403c;
  --c-border:#57534e; --c-text:#fef3c7; --c-text-dim:#d4a574; --c-text-mute:#78716c;
  --c-accent:#f59e0b; --c-accent-2:#fbbf24;
  --c-accent-glow:rgba(245,158,11,.5); --c-accent-bg:rgba(245,158,11,.14);
  --c-accent-border:rgba(245,158,11,.4);
  --c-success:#a3e635; --c-warning:#fbbf24; --c-danger:#fb7185;
  --c-nvidia:#bef264; --c-amd:#fda4af; --c-intel:#93c5fd;
}
body { background-image: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(245,158,11,.15) 0%, transparent 60%), radial-gradient(ellipse 60% 30% at 50% 100%, rgba(180,83,9,.15) 0%, transparent 60%); }
''',
    },
    18: {
        'name': 'Newegg',
        'style': '''
:root {
  --c-bg:#ffffff; --c-surface:#f8fafc; --c-surface-2:#f1f5f9; --c-surface-3:#e2e8f0;
  --c-border:#cbd5e1; --c-text:#0f172a; --c-text-dim:#334155; --c-text-mute:#94a3b8;
  --c-accent:#1d4ed8; --c-accent-2:#1e40af;
  --c-accent-glow:rgba(29,78,216,.25); --c-accent-bg:rgba(29,78,216,.1);
  --c-accent-border:rgba(29,78,216,.3);
  --c-success:#16a34a; --c-warning:#ea580c; --c-danger:#dc2626;
  --c-nvidia:#4d7c0f; --c-amd:#b91c1c; --c-intel:#1e40af;
}
body { background-image: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%); }
''',
    },
    19: {
        'name': 'Editorial',
        'style': '''
:root {
  --c-bg:#fafaf9; --c-surface:#ffffff; --c-surface-2:#f5f5f4; --c-surface-3:#e7e5e4;
  --c-border:#a8a29e; --c-text:#0c0a09; --c-text-dim:#44403c; --c-text-mute:#78716c;
  --c-accent:#dc2626; --c-accent-2:#0c0a09;
  --c-accent-glow:rgba(220,38,38,.2); --c-accent-bg:rgba(220,38,38,.08);
  --c-accent-border:rgba(220,38,38,.3);
  --c-success:#15803d; --c-warning:#b45309; --c-danger:#dc2626;
  --c-nvidia:#15803d; --c-amd:#b91c1c; --c-intel:#1e3a8a;
}
body { background: #fafaf9; }
.listing-thumb, .filter-icon, .vendor-icon, .stat-card, .action-btn { border-radius: 0 !important; }
''',
    },
    20: {
        'name': 'Terminal',
        'style': '''
:root {
  --c-bg:#000000; --c-surface:#0a0a0a; --c-surface-2:#141414; --c-surface-3:#1f1f1f;
  --c-border:#2e2e2e; --c-text:#00ff41; --c-text-dim:#00cc33; --c-text-mute:#5a5a5a;
  --c-accent:#00ff41; --c-accent-2:#ffff00;
  --c-accent-glow:rgba(0,255,65,.35); --c-accent-bg:rgba(0,255,65,.1);
  --c-accent-border:rgba(0,255,65,.4);
  --c-success:#00ff41; --c-warning:#ffff00; --c-danger:#ff5555;
  --c-nvidia:#00ff41; --c-amd:#ff5555; --c-intel:#5af;
}
* { font-family: "Cascadia Code", "Fira Code", "Consolas", "Monaco", monospace !important; }
.listing-thumb, .filter-icon, .vendor-icon { border-radius: 0 !important; }
body::before { content:''; position:fixed; inset:0; background: linear-gradient(rgba(0,255,65,.02) 50%, transparent 50%); background-size: 100% 4px; pointer-events: none; }
''',
    },
})


def _render_palette_new(palette_id):
    p = PALETTES[palette_id]
    return render_template(
        'gpu_palette_base.html',
        palette_id=palette_id,
        palette_name=p['name'],
        palette_style=p['style'],
    )


for _pid in (11, 12, 13, 14, 15, 16, 17, 18, 19, 20):
    def _make_handler(pid):
        def _handler():
            return _render_palette_new(pid)
        _handler.__name__ = f'gpu_palette{pid}_page'
        return _handler
    globals()[f'gpu_palette{_pid}_page'] = _make_handler(_pid)
    app.add_url_rule(f'/gpu-palette{_pid}', view_func=globals()[f'gpu_palette{_pid}_page'])


# Computer modal reimaginings — 10 different patterns (v1-v10)
COMPUTER_MODAL_VERSIONS = {
    1:  ('Bottom Sheet',     'computer_modal_v1.html',  'Slides up from bottom, 85vh max, sticky footer, mobile-friendly.'),
    2:  ('Right Drawer',     'computer_modal_v2.html',  'Slides in from right, 460px wide, 3 tabs (Details/Components/Flag).'),
    3:  ('Workstation',      'computer_modal_v3.html',  'Full-screen 95vw x 95vh split, IDE dark theme, monospace data.'),
    4:  ('Command Palette',  'computer_modal_v4.html',  'Cmd+K spotlight, type to search, peek card expands below.'),
    5:  ('Flag Wizard',      'computer_modal_v5.html',  '4-step guided flow (Category → Components → Message → Confirm).'),
    6:  ('Inline Expand',    'computer_modal_v6.html',  'No overlay, click row to expand in place, other rows reflow.'),
    7:  ('Picture-in-Pic',   'computer_modal_v7.html',  'Floating 340x440 mini-window, bottom-right, draggable.'),
    8:  ('Tabbed Modal',     'computer_modal_v8.html',  'Centered 820x620 with 4 tabs (Specs/Components/Flag/History).'),
    9:  ('IDE Two-Panel',    'computer_modal_v9.html',  'VS Code style: sidebar list + main editor, resizable divider.'),
    10: ('Hover Preview',    'computer_modal_v10.html', '380x460 popover on hover (400ms debounce), no modal interruption.'),
}

def _render_computer_modal(vid):
    name, tpl, desc = COMPUTER_MODAL_VERSIONS[vid]
    return render_template(tpl, version_id=vid, version_name=name, version_desc=desc)

for _vid in range(1, 11):
    def _make_modal_handler(vid):
        def _handler():
            return _render_computer_modal(vid)
        _handler.__name__ = f'computer_modal_v{vid}_page'
        return _handler
    globals()[f'computer_modal_v{_vid}_page'] = _make_modal_handler(_vid)
    app.add_url_rule(f'/computer-modal-v{_vid}', view_func=globals()[f'computer_modal_v{_vid}_page'])


@app.route('/computer-modals')
def computer_modals_index():
    """Overview page linking all 10 modal reimaginings."""
    return render_template('computer_modals_index.html', versions=COMPUTER_MODAL_VERSIONS)


@app.route('/computer-modals/compare')
def computer_modals_compare():
    """Side-by-side visual comparison of all 10 modal variants."""
    return render_template('computer_modals_compare.html', versions=COMPUTER_MODAL_VERSIONS)


@app.route('/modal-screens/<path:filename>')
def modal_screens(filename):
    """Serve modal screenshot files."""
    from flask import send_from_directory
    return send_from_directory('templates/_modal_screens', filename)


@app.route('/cpu')
def cpu_page():
    """CPU listings page."""
    return render_template('cpu.html')


@app.route('/models')
def models_page():
    """Model statistics page."""
    return render_template('models.html')


@app.route('/unmatched')
def unmatched_page():
    """Unmatched listings page."""
    return render_template('unmatched.html')





# the app_context block above. Because the block runs during module import, require_role exists.



@app.route('/api/price-spreads')
@cache_control(max_age=30)
def get_price_spreads():
    """Get models with biggest price spreads (MAX - MIN) per category."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            result = {}
            show_active = request.args.get('active', 'true').lower() == 'true'

            # Categories to analyze with their model join info
            categories = [
                ('gpu', 'matched_gpu_id', 'gpu_reference', 'r.vendor, r.model, r.vram_gb'),
                ('cpu', 'matched_cpu_id', 'cpu_reference', 'r.producer, r.cpu_name, r.processor_number'),
                ('ssd', 'matched_ssd_id', 'ssd_reference', 'r.brand, r.model, r.capacity_gb'),
                ('ram', 'matched_ram_id', 'ram_reference', 'r.name, r.speed, r.capacity_gb'),
                ('psu', 'matched_psu_id', 'psu_reference', 'r.name, r.wattage'),
                ('case', 'matched_case_id', 'case_reference', 'r.name, r.type'),
                ('motherboard', 'motherboard_model_id', 'motherboard_models', 'r.brand, r.model, r.socket, r.chipset'),
                ('monitor', 'monitor_model_id', 'monitor_models', 'r.brand, r.model, r.size, r.resolution, r.refresh_rate'),
            ]

            for cat, match_col, ref_table, model_cols in categories:
                try:
                    active_clause = "AND l.is_active = true" if show_active else ""
                    query = f"""
                        WITH versioned AS (
                            SELECT
                                listing_id,
                                CASE WHEN listing_id ~ '_v\\d+$' THEN regexp_replace(listing_id, '_v\\d+$', '') ELSE listing_id END as base_id,
                                CASE WHEN listing_id ~ '_v(\\d+)$' THEN (regexp_match(listing_id, '_v(\\d+)$'))[1]::int ELSE 0 END as version_num
                            FROM listings
                            WHERE category = %s
                        ),
                        latest_version AS (
                            SELECT base_id, MAX(version_num) as max_version
                            FROM versioned
                            GROUP BY base_id
                        ),
                        latest_listings AS (
                            SELECT l.*
                            FROM listings l
                            JOIN versioned v ON l.listing_id = v.listing_id
                            JOIN latest_version lv ON v.base_id = lv.base_id AND v.version_num = lv.max_version
                            WHERE l.category = %s
                                AND l.{match_col} IS NOT NULL
                                {active_clause}
                                AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                        )
                        SELECT
                            r.id as model_id,
                            {model_cols},
                            COUNT(*) as listing_count,
                            ROUND(MIN(l.price_eur)::numeric, 2) as min_price,
                            ROUND(MAX(l.price_eur)::numeric, 2) as max_price,
                            ROUND((MAX(l.price_eur) - MIN(l.price_eur))::numeric, 2) as price_spread,
                            ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                        FROM latest_listings l
                        JOIN {ref_table} r ON l.{match_col} = r.id
                        GROUP BY r.id, {model_cols}
                        HAVING COUNT(*) >= 2
                        ORDER BY price_spread DESC
                        LIMIT 10
                    """
                    cursor.execute(query, (cat, cat))

                    rows = cursor.fetchall()

                    # Format the data
                    formatted = []
                    for row in rows:
                        row_dict = dict(row)
                        # Calculate spread percentage
                        if row_dict['min_price'] and row_dict['min_price'] > 0:
                            row_dict['spread_percent'] = round(
                                (row_dict['price_spread'] / row_dict['min_price']) * 100, 1
                            )
                        else:
                            row_dict['spread_percent'] = 0
                        formatted.append(row_dict)

                    result[cat] = formatted

                except Exception as e:
                    print(f"Error getting price spreads for {cat}: {e}")
                    conn.rollback()  # Rollback to clear the aborted transaction
                    result[cat] = []

            return jsonify(result)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()


# Project Notes API
import os
from datetime import datetime

NOTES_FILE = r'G:\Github\SS-WEB-SCRAPPER\project_notes.md'

@app.route('/api/project-notes')
@cache_control(max_age=30)
def get_project_notes():
    """Get all project notes."""
    try:
        notes = []
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse notes - each note starts with ## timestamp
                sections = content.split('\n## ')
                for section in sections[1:]:  # Skip first empty section
                    lines = section.split('\n', 1)
                    if lines:
                        timestamp = lines[0].strip()
                        text = lines[1].strip() if len(lines) > 1 else ''
                        notes.append({
                            'timestamp': timestamp,
                            'text': text
                        })
        return jsonify({'notes': notes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/project-notes', methods=['POST'])
def add_project_note():
    """Add a new project note."""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if not text:
            return jsonify({'error': 'Note text is required'}), 400

        # Format the note for markdown
        note_entry = f"\n## {timestamp}\n\n{text}\n"

        # Append to file (create if doesn't exist)
        with open(NOTES_FILE, 'a', encoding='utf-8') as f:
            f.write(note_entry)

        return jsonify({'success': True, 'message': 'Note saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/consoles')
def consoles_page():
    """Console listings page."""
    return render_template('consoles.html')


# ============ Console page reimaginings (v1-v5) ============
CONSOLE_VERSIONS = {
    1: ('Bento Discovery',   'console_v1.html', 'Multi-lens tiles · each tile is a different view (totals, brands, deals, recent, search)'),
    2: ('Compare Tray',      'console_v2.html', 'E-commerce pattern · click 2-4 cards to add to sticky compare tray at bottom'),
    3: ('Rarity Cards',      'console_v3.html', 'Collectible card view · rarity based on price percentile · click to flip'),
    4: ('Deal Feed',         'console_v4.html', 'Algorithmic feed ranked by deal score · Reverb/Discogs style browse'),
    5: ('Latvia Map',        'console_v5.html', 'Geographic view · pins per city · click pin to see local listings'),
}

def _render_console(vid):
    name, tpl, desc = CONSOLE_VERSIONS[vid]
    return render_template(tpl, version_id=vid, version_name=name, version_desc=desc)

for _vid in range(1, 6):
    def _make_console_handler(vid):
        def _handler():
            return _render_console(vid)
        _handler.__name__ = f'console_v{vid}_page'
        return _handler
    globals()[f'console_v{_vid}_page'] = _make_console_handler(_vid)
    app.add_url_rule(f'/console-v{_vid}', view_func=globals()[f'console_v{_vid}_page'])


@app.route('/console-versions')
def console_versions_index():
    """Overview page linking all 5 console page reimaginings."""
    return render_template('console_versions_index.html', versions=CONSOLE_VERSIONS)


@app.route('/pc-builder')
def pc_builder_page():
    """PC Builder page."""
    return render_template('pc_builder.html')


@app.route('/api/consoles/stats')
@cache_control(max_age=30)
def get_console_stats():
    """Get console statistics."""
    cursor = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings
                WHERE category = 'console' OR title ILIKE '%playstation%' OR title ILIKE '%xbox%' OR title ILIKE '%nintendo%'
            """)
            stats = dict(cursor.fetchone())

            cursor.close()

            return jsonify(stats)

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify({
            'total_listings': 0,
            'active_listings': 0,
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0
        })


@app.route('/api/flagged-listings')
@cache_control(max_age=30)
def get_flagged_listings():
    """Get flagged listings."""
    cursor = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if flagged_listings table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'flagged_listings'
                ) as exists
            """)
            row = cursor.fetchone()
            table_exists = row and row.get('exists', False)

            if not table_exists:
                cursor.close()
                return jsonify({'error': 'flagged_listings table does not exist'}), 500

            # Get column names from flagged_listings table
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'flagged_listings'
            """)
            columns = [row['column_name'] for row in cursor.fetchall()]

            # Build query based on available columns
            select_fields = ["fl.id", "fl.listing_id", "fl.reason", "fl.flagged_at", "fl.category",
                              "fl.title AS snapshot_title", "fl.price_eur AS snapshot_price",
                              "fl.seller_location AS snapshot_location", "fl.listing_url AS snapshot_url",
                              "fl.image_url AS snapshot_image"]
            if 'flag_comment' in columns:
                select_fields.append("fl.flag_comment")

            select_fields.extend([
                "l.title AS listings_title",
                "l.price_eur AS listings_price",
                "l.image_url AS listings_image",
                "l.listing_url AS listings_url",
                "l.seller_location AS listings_location",
                "l.category AS listing_category",
                "cl.title AS computer_title",
                "cl.price_eur AS computer_price",
                "cl.image_url AS computer_image",
                "cl.listing_url AS computer_url",
                "cl.seller_location AS computer_location"
            ])

            query = f"""
                SELECT {', '.join(select_fields)}
                FROM flagged_listings fl
                LEFT JOIN listings l ON fl.listing_id = l.listing_id
                LEFT JOIN computer_listings cl ON fl.listing_id = cl.listing_id
                ORDER BY fl.flagged_at DESC
            """

            cursor.execute(query)
            flagged = cursor.fetchall()

            # Convert to dicts and filter by category if requested
            result = [dict(row) for row in flagged]

            # Normalize category source for API consumers
            # Some rows store plural forms (e.g., 'Computers') while listings uses singular ('computer')
            CATEGORY_ALIASES = {
                'computers': 'computer',
                'computer': 'computer',
                'gpus': 'gpu',
                'gpu': 'gpu',
                'cpus': 'cpu',
                'cpu': 'cpu',
                'ssds': 'ssd',
                'ssd': 'ssd',
                'rams': 'ram',
                'ram': 'ram',
                'psus': 'psu',
                'psu': 'psu',
                'cases': 'case',
                'case': 'case',
                'motherboards': 'motherboard',
                'motherboard': 'motherboard',
                'monitors': 'monitor',
                'monitor': 'monitor',
                'lenses': 'lens',
                'lens': 'lens',
                'cameras': 'camera',
                'camera': 'camera',
                'consoles': 'console',
                'console': 'console',
            }

            def canonical_category(cat):
                cat = (cat or '').strip().lower()
                return CATEGORY_ALIASES.get(cat, cat)

            # Coalesce snapshot values with live listing/computer_listing values so exports keep data after deletion
            for item in result:
                item['category'] = canonical_category(
                    item.get('category') or item.get('listing_category')
                )
                item['title'] = (
                    item.get('listings_title')
                    or item.get('computer_title')
                    or item.get('snapshot_title')
                    or ''
                )
                item['price_eur'] = (
                    item.get('listings_price') if item.get('listings_price') is not None
                    else (item.get('computer_price') if item.get('computer_price') is not None
                          else item.get('snapshot_price'))
                )
                item['seller_location'] = (
                    item.get('listings_location')
                    or item.get('computer_location')
                    or item.get('snapshot_location')
                    or ''
                )
                item['listing_url'] = (
                    item.get('listings_url')
                    or item.get('computer_url')
                    or item.get('snapshot_url')
                    or ''
                )
                item['image_url'] = (
                    item.get('listings_image')
                    or item.get('computer_image')
                    or item.get('snapshot_image')
                    or ''
                )

            # Drop helper keys so they don't leak to API consumers
            helper_keys = [
                'listings_title', 'listings_price', 'listings_image', 'listings_url', 'listings_location',
                'computer_title', 'computer_price', 'computer_image', 'computer_url', 'computer_location',
                'snapshot_title', 'snapshot_price', 'snapshot_image', 'snapshot_url', 'snapshot_location',
                'listing_category', 'computer_category'
            ]
            for item in result:
                for key in helper_keys:
                    item.pop(key, None)

            category_filter = canonical_category(request.args.get('category', 'all'))
            if category_filter != 'all':
                result = [item for item in result if item.get('category') == category_filter]

            # Sorting
            sort = request.args.get('sort', 'flagged_at_desc')
            reverse = sort.endswith('_desc')
            if sort.startswith('price'):
                key = lambda x: float(x.get('price_eur') or 0)
            elif sort.startswith('title'):
                key = lambda x: (x.get('title') or '').lower()
            elif sort.startswith('category'):
                key = lambda x: (x.get('category') or '').lower()
            else:
                key = lambda x: x.get('flagged_at') or datetime.min
            result.sort(key=key, reverse=reverse)

            # Pagination: only return metadata when requested
            paginated = request.args.get('limit') is not None or request.args.get('offset') is not None
            if paginated:
                try:
                    limit = max(1, min(1000, int(request.args.get('limit', 25))))
                except ValueError:
                    limit = 25
                try:
                    offset = max(0, int(request.args.get('offset', 0)))
                except ValueError:
                    offset = 0
                total = len(result)
                items = result[offset:offset + limit]
                cursor.close()
                return jsonify({
                    'items': [convert_decimal_to_float(item) for item in items],
                    'total': total,
                    'limit': limit,
                    'offset': offset
                })

            cursor.close()

            return jsonify([convert_decimal_to_float(item) for item in result])

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify({'error': str(e)}), 500


# Alias for admin panel compatibility
@app.route('/api/flagged')
@cache_control(max_age=30)
def get_flagged_alias():
    """Alias for /api/flagged-listings (admin panel compatibility)."""
    return get_flagged_listings()


# Flag a listing (POST endpoint)
@app.route('/api/flag-listing', methods=['POST'])
def flag_listing():
    """Flag a listing with a comment."""
    cursor = None

    data = request.get_json(silent=True) or {}
    listing_id = data.get('listing_id')
    if not listing_id:
        return jsonify({'success': False, 'error': 'listing_id is required'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Create flagged_listings table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flagged_listings (
                    listing_id VARCHAR(255) PRIMARY KEY,
                    reason TEXT,
                    flag_comment TEXT,
                    category VARCHAR(50),
                    title VARCHAR(500),
                    price_eur DECIMAL(10,2),
                    seller_location VARCHAR(200),
                    listing_url TEXT,
                    image_url TEXT,
                    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add flag_comment column if migrating from an older schema
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'flagged_listings' AND column_name = 'flag_comment'
            """)
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE flagged_listings ADD COLUMN flag_comment TEXT")

            # Snapshot current listing details so exports still work if the listing is later deleted
            cursor.execute("""
                SELECT title, price_eur, seller_location, listing_url, image_url, category
                FROM listings WHERE listing_id = %s
            """, (listing_id,))
            listing_row = cursor.fetchone()
            if listing_row:
                snap_title, snap_price, snap_location, snap_url, snap_image, snap_category = listing_row
            else:
                # Try computer_listings for full computer builds
                cursor.execute("""
                    SELECT title, price_eur, seller_location, listing_url, image_url
                    FROM computer_listings WHERE listing_id = %s
                """, (listing_id,))
                comp_row = cursor.fetchone()
                if comp_row:
                    snap_title, snap_price, snap_location, snap_url, snap_image = comp_row
                    snap_category = 'computer'
                else:
                    snap_title = snap_price = snap_location = snap_url = snap_image = snap_category = None

            # reason = flagging category (e.g. ssd_mismatch, spam); comment = human note
            # Some modals send flag_category instead of reason, so accept both.
            reason = data.get('reason') or data.get('flag_category') or comment or 'other'
            flag_comment = data.get('comment', '')

            cursor.execute("""
                INSERT INTO public.flagged_listings (
                    listing_id, reason, flag_comment, category,
                    title, price_eur, seller_location, listing_url, image_url, flagged_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (listing_id) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    flag_comment = EXCLUDED.flag_comment,
                    category = COALESCE(public.flagged_listings.category, EXCLUDED.category),
                    title = COALESCE(public.flagged_listings.title, EXCLUDED.title),
                    price_eur = COALESCE(public.flagged_listings.price_eur, EXCLUDED.price_eur),
                    seller_location = COALESCE(public.flagged_listings.seller_location, EXCLUDED.seller_location),
                    listing_url = COALESCE(public.flagged_listings.listing_url, EXCLUDED.listing_url),
                    image_url = COALESCE(public.flagged_listings.image_url, EXCLUDED.image_url),
                    flagged_at = CURRENT_TIMESTAMP
            """, (
                listing_id, reason, flag_comment, snap_category,
                snap_title, snap_price, snap_location, snap_url, snap_image
            ))

            conn.commit()
            cursor.close()

            return jsonify({'success': True, 'message': 'Listing flagged'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


# Unflag a listing
@app.route('/api/unflag', methods=['POST'])
def unflag_listing():
    """Remove flag from a listing."""
    cursor = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM flagged_listings WHERE listing_id = %s", (listing_id,))
            conn.commit()
            cursor.close()

            return jsonify({'success': True, 'message': 'Flag removed'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/cameras')
def cameras_page():
    """Camera listings page."""
    return render_template('cameras.html')


@app.route('/api/cameras')
@cache_control(max_age=30)
def get_cameras():
    """Get camera listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            brand_filter = request.args.get('brand', '')
            model_filter = request.args.get('model', '')
            sensor_filter = request.args.get('sensor', '')

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.description,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.image_url,
                    l.listing_url,
                    l.matched_camera_id,
                    c.brand as camera_brand,
                    c.model as camera_model,
                    c.sensor as sensor_type,
                    c.resolution as megapixels
                FROM listings l
                LEFT JOIN camera_reference c ON l.matched_camera_id::integer = c.id
                WHERE l.category = 'camera'
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('camera')
            if brand_filter:
                query += " AND c.brand ILIKE %s"
                params.append(f'%{brand_filter}%')
            if model_filter:
                query += " AND c.model ILIKE %s"
                params.append(f'%{model_filter}%')
            if sensor_filter:
                query += " AND c.sensor ILIKE %s"
                params.append(f'%{sensor_filter}%')

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Compute latest first_seen_at date for NEW badge.
            latest_first_seen = None
            try:
                cursor.execute("""
                    SELECT MAX(first_seen_at::date) as latest_date
                    FROM listings
                    WHERE category = 'camera' AND first_seen_at IS NOT NULL
                """)
                result = cursor.fetchone()
                latest_first_seen = result['latest_date'] if result and result['latest_date'] else None
            except Exception:
                pass

            # Compute per-camera model statistics for UNICORN and STEAL badges.
            # Count is all-time, excluding flagged listings.
            camera_stats = {}
            try:
                cursor.execute("""
                    SELECT
                        l.matched_camera_id,
                        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'camera'
                      AND l.matched_camera_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM flagged_listings fl
                          WHERE fl.listing_id = l.listing_id
                            AND fl.is_active = true
                      )
                    GROUP BY l.matched_camera_id
                """)
                for row in cursor.fetchall():
                    camera_stats[row['matched_camera_id']] = dict(row)
            except Exception:
                pass

            # Get all lens references for lens detection
            cursor.execute("""
                SELECT
                    lens_name,
                    focal_length_mm,
                    max_focal_length_mm,
                    max_aperture
                FROM lens_reference
                WHERE lens_name IS NOT NULL
            """)
            all_lenses = cursor.fetchall()

            # Convert to dict and handle Decimal, add lens detection
            listings_dict = []
            for row in listings:
                row_dict = convert_decimal_to_float(dict(row))

                # NEW badge: current import date for camera category
                if latest_first_seen and row_dict.get('first_seen_at'):
                    fs = row_dict['first_seen_at']
                    listing_date = fs.date() if hasattr(fs, 'date') else fs
                    row_dict['is_new'] = listing_date == latest_first_seen
                else:
                    row_dict['is_new'] = False

                # UNICORN badge + price stats per matched_camera_id
                matched_id = row_dict.get('matched_camera_id')
                if matched_id and matched_id in camera_stats:
                    stats = camera_stats[matched_id]
                    current_price = float(row_dict.get('price_eur', 0))
                    avg_price = float(stats['avg_price']) if stats['avg_price'] else 0
                    min_price = float(stats['min_price']) if stats['min_price'] else 0
                    max_price = float(stats['max_price']) if stats['max_price'] else 0
                    count = int(stats['listing_count']) if stats['listing_count'] else 0

                    row_dict['is_unicorn'] = count == 1
                    if count > 1:
                        row_dict['price_stats'] = {
                            'avg': avg_price,
                            'min': min_price,
                            'max': max_price,
                            'below_avg': current_price < avg_price,
                            'percentile': round((current_price - min_price) / (max_price - min_price) * 100, 1)
                                          if max_price > min_price else 50,
                            'listing_count': count
                        }
                    else:
                        row_dict['price_stats'] = None
                else:
                    row_dict['is_unicorn'] = False

                # Detect lenses from title and description
                search_text = (row_dict.get('title', '') + ' ' + row_dict.get('description', '')).lower()
                detected_lenses = []

                for lens in all_lenses:
                    lens_name = lens['lens_name']
                    if not lens_name:
                        continue

                    lens_patterns = [
                        lens_name.lower(),
                        lens_name.lower().replace('_', ' ').replace('-', ' ')
                    ]

                    lens_found = False
                    for pattern in set(lens_patterns):
                        if pattern in search_text:
                            lens_found = True
                            break

                    # Also check for focal length + aperture pattern
                    if not lens_found and lens['focal_length_mm']:
                        focal = str(lens['focal_length_mm'])
                        aperture = str(lens['max_aperture']) if lens['max_aperture'] else None

                        if aperture:
                            focal_aperture_patterns = [
                                f"{focal}mm f/{aperture}",
                                f"{focal}mm f{aperture}",
                                f"{focal}mm {aperture}",
                                f"{focal} mm f/{aperture}",
                                f"{focal}mm 1:{aperture}",
                            ]

                            for pattern in focal_aperture_patterns:
                                if pattern in search_text:
                                    lens_found = True
                                    break

                    if lens_found:
                        focal_display = str(lens['focal_length_mm'])
                        if lens['max_focal_length_mm'] and lens['max_focal_length_mm'] != lens['focal_length_mm']:
                            focal_display = f"{lens['focal_length_mm']}-{lens['max_focal_length_mm']}"

                        detected_lenses.append({
                            'name': lens['lens_name'].replace('_', ' '),
                            'focal_length': focal_display + 'mm' if focal_display else None
                        })

                # Remove duplicates
                seen = set()
                unique_lenses = []
                for lens in detected_lenses:
                    if lens['name'] not in seen:
                        seen.add(lens['name'])
                        unique_lenses.append(lens)

                row_dict['detected_lenses'] = unique_lenses
                listings_dict.append(row_dict)

            # Get stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_active THEN 1 END) as active,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price
                FROM listings
                WHERE category = 'camera'
            """)
            stats_row = cursor.fetchone()
            stats = convert_decimal_to_float(dict(stats_row)) if stats_row else {'total': 0, 'active': 0, 'avg_price': 0}

            cursor.close()

            return jsonify({
                'success': True,
                'listings': listings_dict,
                'stats': stats
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            if cursor:
                cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/stats')
@cache_control(max_age=30)
def get_camera_stats():
    """Get camera statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    COUNT(CASE WHEN matched_camera_id IS NOT NULL THEN 1 END) as matched,
                    COUNT(CASE WHEN matched_camera_id IS NULL THEN 1 END) as unmatched,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings
                WHERE category = 'camera'
            """)
            stats = dict(cursor.fetchone())

            # Get stats by brand
            cursor.execute("""
                SELECT
                    c.brand,
                    COUNT(*) as count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                FROM listings l
                JOIN camera_reference c ON l.matched_camera_id::integer = c.id
                WHERE l.category = 'camera' AND l.is_active = true
                GROUP BY c.brand
                ORDER BY count DESC
            """)
            brands = cursor.fetchall()

            # Get stats by sensor type (using 'sensor' column)
            cursor.execute("""
                SELECT
                    c.sensor as sensor_type,
                    COUNT(*) as count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                FROM listings l
                JOIN camera_reference c ON l.matched_camera_id::integer = c.id
                WHERE l.category = 'camera' AND l.is_active = true AND c.sensor IS NOT NULL
                GROUP BY c.sensor
                ORDER BY count DESC
            """)
            sensors = cursor.fetchall()

            cursor.close()

            result = {
                'success': True,
                'overall': convert_decimal_to_float(stats),
                'by_brand': [convert_decimal_to_float(dict(row)) for row in brands],
                'by_sensor': [convert_decimal_to_float(dict(row)) for row in sensors]
            }

            return jsonify(result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            if cursor:
                cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/camera-brands')
@cache_control(max_age=30)
def get_camera_brands():
    """Get list of camera brands."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT DISTINCT brand FROM camera_reference
                WHERE brand IS NOT NULL AND brand != ''
                ORDER BY brand
            """)
            brands = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return jsonify(brands)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if cursor:
                cursor.close()
            return jsonify([]), 500


@app.route('/api/camera-models')
@cache_control(max_age=30)
def get_camera_models():
    """Get camera model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            brand_filter = request.args.get('brand', '')

            if brand_filter:
                # Get models for a specific brand
                cursor.execute("""
                    SELECT DISTINCT model FROM camera_reference
                    WHERE brand ILIKE %s AND model IS NOT NULL
                    ORDER BY model
                """, (f'%{brand_filter}%',))
                models = [row['model'] for row in cursor.fetchall()]
                cursor.close()
                return jsonify(models)
            else:
                # Get full model stats
                cursor.execute("""
                    SELECT
                        c.id,
                        c.brand,
                        c.model,
                        c.sensor as sensor_type,
                        COUNT(l.listing_id) as active_listings,
                        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price
                    FROM camera_reference c
                    JOIN listings l ON c.id = l.matched_camera_id::integer
                    WHERE l.category = 'camera' AND l.is_active = true
                    GROUP BY c.id, c.brand, c.model, c.sensor
                    ORDER BY avg_price DESC
                """)

                models = cursor.fetchall()
                cursor.close()

                return jsonify([convert_decimal_to_float(dict(row)) for row in models])

        except Exception as e:
            import traceback
            traceback.print_exc()
            if cursor:
                cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/camera-listing-details/<listing_id>')
@cache_control(max_age=30)
def get_camera_listing_details(listing_id):
    """Get detailed information for a camera listing including lenses."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get the listing with camera info
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.description,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.image_url,
                    l.listing_url,
                    l.matched_camera_id,
                    c.brand as camera_brand,
                    c.model as camera_model,
                    c.sensor as sensor_type,
                    c.resolution as megapixels,
                    c.release_year,
                    c.resolution,
                    c.fps,
                    c.iso,
                    c.focus_points,
                    c.video_specs,
                    c.battery,
                    c.storage,
                    c.screen,
                    c.mount as camera_mount
                FROM listings l
                LEFT JOIN camera_reference c ON l.matched_camera_id::integer = c.id
                WHERE l.listing_id = %s AND l.category = 'camera'
            """, (listing_id,))

            listing = cursor.fetchone()
            if not listing:
                cursor.close()
                return jsonify({'success': False, 'error': 'Listing not found'}), 404

            listing_dict = convert_decimal_to_float(dict(listing))

            # Build unified lenses list from DB-matched matched_lens_id first
            unified_lenses = []
            seen_lens_ids = set()

            if listing_dict.get('matched_lens_id'):
                lens_names = listing_dict['matched_lens_id']
                if isinstance(lens_names, str):
                    lens_name_list = [n.strip() for n in lens_names.split(',') if n.strip()]
                else:
                    lens_name_list = [str(lens_names)]

                for lens_name in lens_name_list:
                    cursor.execute("""
                        SELECT id, lens_name, brand, mount, focal_length_mm,
                               max_focal_length_mm, max_aperture, price_new
                        FROM lens_reference
                        WHERE lens_name = %s
                    """, (lens_name,))
                    lens_row = cursor.fetchone()
                    if lens_row:
                        lens_data = dict(lens_row)
                        lens_id = lens_data.get('id')
                        if lens_id in seen_lens_ids:
                            continue
                        seen_lens_ids.add(lens_id)

                        focal_display = str(int(lens_data['focal_length_mm'])) if lens_data['focal_length_mm'] else None
                        if lens_data['max_focal_length_mm'] and lens_data['max_focal_length_mm'] != lens_data['focal_length_mm']:
                            focal_display = f"{int(lens_data['focal_length_mm'])}-{int(lens_data['max_focal_length_mm'])}"

                        unified_lenses.append({
                            'id': lens_id,
                            'slug': lens_data['lens_name'],
                            'name': lens_data['lens_name'].replace('_', ' '),
                            'brand': lens_data['brand'],
                            'mount_type': lens_data['mount'],
                            'focal_length': focal_display + 'mm' if focal_display else None,
                            'aperture': f"f/{lens_data['max_aperture']}" if lens_data['max_aperture'] else None,
                            'estimated_value': float(lens_data['price_new']) if lens_data['price_new'] else None,
                            'match_source': 'database'
                        })

            # Detect additional lenses from title and description (runtime detection)
            cursor.execute("""
                SELECT
                    lens_name,
                    brand,
                    mount,
                    focal_length_mm,
                    max_focal_length_mm,
                    max_aperture,
                    price_new
                FROM lens_reference
                WHERE lens_name IS NOT NULL
            """)
            all_lenses = cursor.fetchall()

            title_text = listing_dict.get('title') or ''
            desc_text = listing_dict.get('description') or ''
            search_text = (title_text + ' ' + desc_text).lower()
            camera_brand = (listing_dict.get('camera_brand') or '').lower()

            for lens in all_lenses:
                lens_name = lens['lens_name']
                if not lens_name:
                    continue

                lens_name_lower = lens_name.lower()
                lens_name_clean = lens_name_lower.replace('_', ' ').replace('-', ' ')

                exact_matches = [
                    lens_name_lower,
                    lens_name_clean,
                    lens_name_lower.replace('_', ''),
                ]

                lens_found = False
                for match_pattern in exact_matches:
                    if match_pattern in search_text:
                        lens_found = True
                        break

                if not lens_found and camera_brand:
                    lens_brand = (lens['brand'] or '').lower()
                    if lens_brand and camera_brand == lens_brand:
                        if lens['focal_length_mm'] and lens['max_aperture']:
                            focal = str(int(lens['focal_length_mm']))
                            aperture = str(lens['max_aperture'])
                            focal_in_text = f"{focal}mm" in search_text or f"{focal} mm" in search_text
                            aperture_in_text = f"f/{aperture}" in search_text or f"1:{aperture}" in search_text
                            if focal_in_text and aperture_in_text:
                                lens_found = True

                if lens_found:
                    cursor.execute("SELECT id FROM lens_reference WHERE lens_name = %s", (lens_name,))
                    lens_row = cursor.fetchone()
                    lens_id = lens_row['id'] if lens_row else None
                    if lens_id and lens_id in seen_lens_ids:
                        continue
                    if lens_id:
                        seen_lens_ids.add(lens_id)

                    estimated_value = float(lens['price_new']) if lens['price_new'] else None
                    focal_display = str(int(lens['focal_length_mm'])) if lens['focal_length_mm'] else None
                    if lens['max_focal_length_mm'] and lens['max_focal_length_mm'] != lens['focal_length_mm']:
                        focal_display = f"{int(lens['focal_length_mm'])}-{int(lens['max_focal_length_mm'])}"

                    unified_lenses.append({
                        'id': lens_id,
                        'slug': lens['lens_name'],
                        'name': lens['lens_name'].replace('_', ' '),
                        'brand': lens['brand'],
                        'mount_type': lens['mount'],
                        'focal_length': focal_display + 'mm' if focal_display else None,
                        'aperture': f"f/{lens['max_aperture']}" if lens['max_aperture'] else None,
                        'estimated_value': estimated_value,
                        'match_source': 'text_detection'
                    })

            # Limit to top matches if too many
            if len(unified_lenses) > 3:
                prioritized = []
                for lens in unified_lenses:
                    lens_name_clean = lens['name'].lower().replace(' ', '')
                    if lens_name_clean in search_text.replace(' ', ''):
                        prioritized.insert(0, lens)
                    else:
                        prioritized.append(lens)
                unified_lenses = prioritized[:3]

            # Calculate cost breakdown using all unified lenses
            cost_breakdown = None
            if listing_dict.get('camera_brand'):
                # Get average price for this camera model
                cursor.execute("""
                    SELECT ROUND(AVG(price_eur)::numeric, 2) as avg_price
                    FROM listings
                    WHERE matched_camera_id = %s AND is_active = true AND listing_id != %s
                """, (listing_dict.get('matched_camera_id'), listing_id))
                avg_camera_price = cursor.fetchone()

                # Convert Decimal to float immediately
                from decimal import Decimal
                if avg_camera_price and avg_camera_price['avg_price']:
                    if isinstance(avg_camera_price['avg_price'], Decimal):
                        camera_value = float(avg_camera_price['avg_price'])
                    else:
                        camera_value = float(avg_camera_price['avg_price'])
                else:
                    camera_value = float(listing_dict.get('price_eur', 0)) * 0.7

                # Calculate lenses value from unified lenses
                lenses_value = sum(l.get('estimated_value', 0) or 0 for l in unified_lenses)

                total_market_value = camera_value + lenses_value
                listing_price = float(listing_dict.get('price_eur', 0))

                cost_breakdown = {
                    'camera_value': camera_value,
                    'lenses_value': lenses_value,
                    'total_market_value': total_market_value,
                    'listing_price': listing_price,
                    'savings_indication': (total_market_value - listing_price) if total_market_value and listing_price else None
                }

            cursor.close()

            return jsonify({
                'success': True,
                'listing': listing_dict,
                'lenses': unified_lenses,
                'cost_breakdown': cost_breakdown
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            if cursor:
                cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


# Lenses routes
@app.route('/api/lens-details/<lens_id>')
@cache_control(max_age=30)
def get_lens_details(lens_id):
    """Get lens details and all listings for a specific lens."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get lens info by lens_name (since matched_lens_id stores lens_name)
            cursor.execute("""
                SELECT * FROM lens_reference
                WHERE lens_name = %s
            """, (lens_id,))
            row = cursor.fetchone()
            lens_info = dict(row) if row else {}

            # Get all listings for this lens (matched_lens_id stores lens_name)
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.is_active,
                    l.image_url,
                    l.listing_url
                FROM listings l
                WHERE l.matched_lens_id = %s AND l.category = 'lens'
                ORDER BY l.date_posted DESC
            """, (lens_id,))
            listings = [dict(row) for row in cursor.fetchall()]

            # Calculate stats
            prices = [l['price_eur'] for l in listings if l.get('price_eur')]
            stats = {
                'total_listings': len(listings),
                'active_count': sum(1 for l in listings if l.get('is_active')),
                'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0
            }

            cursor.close()

            return jsonify({
                'lens_info': convert_decimal_to_float(lens_info),
                'listings': [convert_decimal_to_float(l) for l in listings],
                'stats': convert_decimal_to_float(stats)
            })

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/lenses')
def lenses_page():
    """Lenses listings page."""
    return render_template('lenses.html')


@app.route('/lens-compare')
def lens_compare_page():
    """Lenses side-by-side comparison page."""
    return render_template('lens_compare.html')


@app.route('/api/lenses')
@cache_control(max_age=30)
def get_lenses():
    """Get lens listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            mount_filter = request.args.get('mount', '')
            model_filter = request.args.get('model', '')
            source_filter = request.args.get('source', '')
            brand_filter = request.args.get('brand', '')
            match_filter = request.args.get('match_status', 'all')  # all, matched, unknown

            # Build a fuzzy reference map for lens brand/mount enrichment.
            # matched_lens_id is a generated slug, not lens_reference.lens_name,
            # so we match by normalized substring (same logic as get_lens_models).
            cursor.execute("""
                SELECT id, brand, lens_name, focal_length_mm, max_aperture, mount
                FROM lens_reference
            """)
            refs = cursor.fetchall()

            # Load active flagged listing IDs.
            flagged_ids = set()
            try:
                cursor.execute("""
                    SELECT l.listing_id
                    FROM flagged_listings fl
                    JOIN listings l ON fl.listing_id = l.listing_id
                    WHERE fl.is_active = true AND l.category = 'lens'
                """)
                flagged_ids = {row['listing_id'] for row in cursor.fetchall()}
            except Exception:
                pass

            import re
            def normalize(s):
                s = (s or '').lower()
                s = s.replace('_', ' ').replace('-', ' ').replace('f/', 'f ')
                s = re.sub(r'\s+', ' ', s).strip()
                return s

            ref_map = {}
            for ref in refs:
                n = normalize(ref['lens_name'])
                if n not in ref_map:
                    ref_map[n] = ref

            def find_ref(matched_id):
                if not matched_id:
                    return None
                nl = normalize(matched_id)
                for nref, r in ref_map.items():
                    if nref in nl or nl in nref:
                        return r
                return None

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.matched_lens_id,
                    l.source,
                    l.confidence_score
                FROM listings l
                WHERE l.category = 'lens'
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('lens')

            # Match status filter (matched vs unknown)
            if match_filter == 'matched':
                query += " AND l.matched_lens_id IS NOT NULL"
            elif match_filter == 'unknown':
                query += " AND l.matched_lens_id IS NULL"

            # Model filter - exact match on matched_lens_id
            if model_filter:
                query += " AND l.matched_lens_id = %s"
                params.append(model_filter)

            if source_filter and source_filter.lower() != 'all':
                query += " AND l.source = %s"
                params.append(source_filter)

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir}"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Compute latest first_seen_at date for NEW badge.
            latest_first_seen = None
            try:
                cursor.execute("""
                    SELECT MAX(first_seen_at::date) as latest_date
                    FROM listings
                    WHERE category = 'lens' AND first_seen_at IS NOT NULL
                """)
                result = cursor.fetchone()
                latest_first_seen = result['latest_date'] if result and result['latest_date'] else None
            except Exception:
                pass

            # Compute per-lens model statistics for UNICORN and STEAL badges.
            # Count is all-time, excluding flagged listings, to match GPU behavior.
            lens_stats = {}
            try:
                cursor.execute("""
                    SELECT
                        l.matched_lens_id,
                        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM listings l
                    WHERE l.category = 'lens'
                      AND l.matched_lens_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM flagged_listings fl
                          WHERE fl.listing_id = l.listing_id
                            AND fl.is_active = true
                      )
                    GROUP BY l.matched_lens_id
                """)
                for row in cursor.fetchall():
                    lens_stats[row['matched_lens_id']] = dict(row)
            except Exception:
                pass

            # Enrich with lens_reference data, flag status, and apply brand/mount filters.
            result = []
            for row in listings:
                item = dict(row)
                ref = find_ref(item.get('matched_lens_id'))
                if ref:
                    item['brand'] = ref['brand']
                    item['mount'] = ref['mount']
                    item['focal_length_mm'] = ref['focal_length_mm']
                    item['max_aperture'] = ref['max_aperture']
                else:
                    item['brand'] = None
                    item['mount'] = None
                    item['focal_length_mm'] = None
                    item['max_aperture'] = None

                item['is_flagged'] = item['listing_id'] in flagged_ids

                # Default active flag status to true for clients that expect it.
                if 'is_active_flag' not in item:
                    item['is_active_flag'] = True

                # NEW badge: current import date for lens category
                if latest_first_seen and item.get('first_seen_at'):
                    fs = item['first_seen_at']
                    listing_date = fs.date() if hasattr(fs, 'date') else fs
                    item['is_new'] = listing_date == latest_first_seen
                else:
                    item['is_new'] = False

                # UNICORN badge + price stats per matched_lens_id
                matched_id = item.get('matched_lens_id')
                if matched_id and matched_id in lens_stats:
                    stats = lens_stats[matched_id]
                    current_price = float(item.get('price_eur', 0))
                    avg_price = float(stats['avg_price']) if stats['avg_price'] else 0
                    min_price = float(stats['min_price']) if stats['min_price'] else 0
                    max_price = float(stats['max_price']) if stats['max_price'] else 0
                    count = int(stats['listing_count']) if stats['listing_count'] else 0

                    item['is_unicorn'] = count == 1
                    if count > 1:
                        item['price_stats'] = {
                            'avg': avg_price,
                            'min': min_price,
                            'max': max_price,
                            'below_avg': current_price < avg_price,
                            'percentile': round((current_price - min_price) / (max_price - min_price) * 100, 1)
                                          if max_price > min_price else 50,
                            'listing_count': count
                        }
                    else:
                        item['price_stats'] = None
                else:
                    item['is_unicorn'] = False

                if brand_filter and brand_filter.lower() != 'all':
                    if not item.get('brand') or brand_filter.lower() not in item['brand'].lower():
                        continue
                if mount_filter:
                    if not item.get('mount') or mount_filter.lower() != item['mount'].lower():
                        continue

                result.append(convert_decimal_to_float(item))

            cursor.close()

            return jsonify(result[:100])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/lens-brands')
@cache_control(max_age=30)
def get_lens_brands():
    """Get unique lens brands."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT DISTINCT brand FROM lens_reference
                WHERE brand IS NOT NULL AND brand != ''
                ORDER BY brand
            """)
            brands = [row['brand'] for row in cursor.fetchall()]
            cursor.close()

            return jsonify(brands)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/lens-models')
@cache_control(max_age=30)
def get_lens_models():
    """Get lens model statistics keyed by listing matched_lens_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            brand_filter = request.args.get('brand', '')
            mount_filter = request.args.get('mount', '')

            # Aggregate active lens listings by their matched_lens_id
            cursor.execute("""
                SELECT
                    matched_lens_id,
                    COUNT(listing_id) as active_listings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings
                WHERE category = 'lens' AND is_active = true AND matched_lens_id IS NOT NULL
                GROUP BY matched_lens_id
                ORDER BY active_listings DESC
            """)
            listing_groups = cursor.fetchall()

            # Fetch lens references for brand/mount enrichment and filtering
            cursor.execute("""
                SELECT id, brand, lens_name, focal_length_mm, max_aperture, mount
                FROM lens_reference
            """)
            refs = cursor.fetchall()

            import re
            def normalize(s):
                s = (s or '').lower()
                s = s.replace('_', ' ').replace('-', ' ').replace('f/', 'f ')
                s = re.sub(r'\s+', ' ', s).strip()
                return s

            ref_map = {}
            for ref in refs:
                n = normalize(ref['lens_name'])
                if n not in ref_map:
                    ref_map[n] = ref

            models = []
            for g in listing_groups:
                matched_id = g['matched_lens_id']
                nl = normalize(matched_id)
                ref = None
                for nref, r in ref_map.items():
                    if nref in nl or nl in nref:
                        ref = r
                        break

                if brand_filter:
                    if not ref or not ref['brand'] or brand_filter.lower() not in ref['brand'].lower():
                        continue
                if mount_filter:
                    if not ref or not ref['mount'] or mount_filter.lower() not in ref['mount'].lower():
                        continue

                model = {
                    'id': ref['id'] if ref else None,
                    'brand': ref['brand'] if ref else None,
                    'matched_lens_id': matched_id,
                    'focal_length': ref['focal_length_mm'] if ref else None,
                    'aperture': ref['max_aperture'] if ref else None,
                    'mount': ref['mount'] if ref else None,
                    'active_listings': g['active_listings'],
                    'avg_price': float(g['avg_price']) if g['avg_price'] is not None else None,
                    'min_price': float(g['min_price']) if g['min_price'] is not None else None,
                    'max_price': float(g['max_price']) if g['max_price'] is not None else None,
                }
                models.append(convert_decimal_to_float(model))

            return jsonify(models)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()


@app.route('/api/lens-mounts')
@cache_control(max_age=30)
def get_lens_mounts():
    """Get unique lens mounts."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT DISTINCT mount FROM lens_reference
                WHERE mount IS NOT NULL AND mount != ''
                ORDER BY mount
            """)
            mounts = [row['mount'] for row in cursor.fetchall()]
            cursor.close()

            return jsonify(mounts)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


# Motherboards routes
@app.route('/motherboards')
def motherboards_page():
    """Motherboard listings page."""
    return render_template('motherboards.html')


@app.route('/api/motherboards')
@cache_control(max_age=30)
def get_motherboards():
    """Get motherboard listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            chipset_filter = request.args.get('chipset', '')
            socket_filter = request.args.get('socket', '')
            cpu_filter = request.args.get('cpu', '')  # NEW: CPU filter
            vendor_filter = request.args.get('vendor', '')  # NEW: Vendor filter (Intel/AMD)
            model_filter = request.args.get('model', '').strip()  # NEW: motherboard model filter (used by /api/motherboards/lookup)
            time_filter = request.args.get('time', 'all_time')
            min_confidence = float(request.args.get('min_confidence', 0))

            # Check if motherboard_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            # NEW: If CPU filter provided, get socket from CPU
            cpu_socket = None
            cpu_chipset_filter = None
            if cpu_filter:
                cpu_id_param = cpu_filter if cpu_filter.isdigit() else None
                if cpu_id_param:
                    cursor.execute("""
                        SELECT socket, processor_number, cpu_name FROM cpu_reference
                        WHERE id = %s OR cpu_name ILIKE %s OR processor_number ILIKE %s
                        LIMIT 1
                    """, (int(cpu_id_param), f'%{cpu_filter}%', f'%{cpu_filter}%'))
                else:
                    cursor.execute("""
                        SELECT socket, processor_number, cpu_name FROM cpu_reference
                        WHERE cpu_name ILIKE %s OR processor_number ILIKE %s
                        LIMIT 1
                    """, (f'%{cpu_filter}%', f'%{cpu_filter}%'))
                cpu_row = cursor.fetchone()
                if cpu_row and cpu_row['socket']:
                    cpu_socket = cpu_row['socket']
                    # Bug 18: same chipset-generation filter as the socket-market
                    # endpoint. Without this, an i7-6700 (gen 6) search would
                    # include H310/B360/Z390 motherboards, which physically
                    # fit the LGA 1151 socket but only work with 8th/9th gen.
                    import re as _re
                    proc_num = (cpu_row.get('processor_number') or '').strip()
                    m = _re.search(r'-?(\d)\d{3}', proc_num) or _re.search(r'(\d)\d{3}', cpu_row.get('cpu_name', '') or '')
                    if m:
                        cpu_generation = int(m.group(1))
                        if cpu_generation in (6, 7) and cpu_socket in ('LGA1151', 'LGA 1151'):
                            cpu_chipset_filter = ['H110', 'B150', 'H170', 'Q170', 'Z170']
                        elif cpu_generation in (8, 9) and cpu_socket in ('LGA1151', 'LGA 1151'):
                            cpu_chipset_filter = ['H310', 'B360', 'H370', 'Q370', 'Z370', 'B365', 'Z390']

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.motherboard_confidence_score as confidence_score,
                    l.motherboard_match_method as match_method,
                    l.motherboard_model_id,
                    m.brand,
                    m.model as motherboard_model,
                    m.socket,
                    m.form_factor,
                    m.chipset
                FROM listings l
                LEFT JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard'
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('motherboard')
            if min_confidence > 0:
                query += " AND COALESCE(l.motherboard_confidence_score, 0) >= %s"
                params.append(min_confidence)
            if chipset_filter:
                query += " AND m.chipset ILIKE %s"
                params.append(f'%{chipset_filter}%')
            if socket_filter:
                query += " AND m.socket = %s"
                params.append(socket_filter)
            if model_filter:
                # Match the model name as a standalone token (case-insensitive).
                # Use ILIKE on the full brand+model to also catch partial model
                # strings (e.g. "PRO H610M-E" matches "MSI PRO H610M-E DDR4").
                query += " AND ((m.brand || ' ' || m.model) ILIKE %s OR m.model ILIKE %s)"
                params.append(f'%{model_filter}%')
                params.append(f'%{model_filter}%')

            # NEW: Filter by CPU socket if CPU selected
            if cpu_socket:
                query += " AND m.socket = %s"
                params.append(cpu_socket)

            # Bug 18: filter chipsets by CPU generation
            if cpu_chipset_filter:
                query += " AND m.chipset = ANY(%s)"
                params.append(cpu_chipset_filter)

            # NEW: Filter by Vendor (Intel/AMD)
            if vendor_filter:
                if vendor_filter.lower() == 'intel':
                    # Intel sockets: LGA1700, LGA1200, LGA1151, LGA1150, LGA2066, etc.
                    query += " AND (m.socket LIKE 'LGA%%' OR m.socket LIKE 'Socket 4%%')"
                elif vendor_filter.lower() == 'amd':
                    # AMD sockets: AM4, AM5, TR4, sTRX4, sWRX8
                    query += " AND (m.socket LIKE 'AM%%' OR m.socket LIKE 'TR%%' OR m.socket LIKE 'sTR%%' OR m.socket LIKE 'sWR%%')"

            query += get_time_filter_sql(time_filter, 'l')

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Get price stats for each model (same resolution as CPU/GPU price_stats)
            cursor.execute("""
                SELECT
                    m.id,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(*) as listing_count
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                GROUP BY m.id
            """)

            model_stats_rows = cursor.fetchall()
            model_stats_map = {}
            for row in model_stats_rows:
                model_stats_map[row['id']] = {
                    'avg': float(row['avg_price']) if row['avg_price'] else 0,
                    'min': float(row['min_price']) if row['min_price'] else 0,
                    'max': float(row['max_price']) if row['max_price'] else 0,
                    'count': row['listing_count']
                }

            # Get chipset stats for the chipset position bar (unchanged)
            cursor.execute("""
                SELECT
                    m.chipset,
                    COUNT(*) as listing_count,
                    AVG(l.price_eur) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                GROUP BY m.chipset
            """)

            chipset_stats_rows = cursor.fetchall()
            chipset_stats_map = {}
            for row in chipset_stats_rows:
                chipset_stats_map[row['chipset']] = {
                    'avg': float(row['avg_price']) if row['avg_price'] else 0,
                    'min': float(row['min_price']) if row['min_price'] else 0,
                    'max': float(row['max_price']) if row['max_price'] else 0,
                    'count': row['listing_count']
                }

            result = []
            for row in listings:
                row_dict = dict(row)
                row_dict = convert_decimal_to_float(row_dict)

                # Add model-level price stats for NEW/STEAL tags
                model_id = row_dict.get('motherboard_model_id')
                if model_id and model_id in model_stats_map:
                    stats = model_stats_map[model_id]
                    current_price = row_dict.get('price_eur', 0)
                    row_dict['price_stats'] = {
                        'avg': stats['avg'],
                        'min': stats['min'],
                        'max': stats['max'],
                        'below_avg': current_price < stats['avg'] if stats['avg'] else False,
                        'percentile': round((current_price - stats['min']) /
                                          (stats['max'] - stats['min']) * 100, 1)
                                          if stats['max'] > stats['min'] else 50,
                        'listing_count': stats['count']
                    }

                # Add chipset stats for this listing
                chipset = row_dict.get('chipset')
                if chipset and chipset in chipset_stats_map:
                    stats = chipset_stats_map[chipset]
                    current_price = row_dict.get('price_eur', 0)
                    row_dict['chipset_stats'] = {
                        'avg': stats['avg'],
                        'min': stats['min'],
                        'max': stats['max'],
                        'count': stats['count'],
                        'below_avg': current_price < stats['avg'] if stats['avg'] else False,
                        'position': min(100, int((current_price - stats['min']) / (stats['max'] - stats['min']) * 100)) if stats['max'] > stats['min'] else 50
                    }

                # Mark as new if this listing is from the latest import for motherboard category
                row_dict['is_new'] = is_listing_new(row_dict.get('first_seen_at'), 'motherboard')

                result.append(row_dict)

            cursor.close()

            return jsonify(result)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/motherboards/stats')
@cache_control(max_age=30)
def get_motherboard_stats():
    """Get motherboard statistics including year/platform/socket distributions."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if motherboard_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify({'success': True, 'stats': {
                    'total_listings': 0,
                    'active_listings': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0,
                    'matched_count': 0,
                    'unmatched_count': 0,
                    'year_distribution': [],
                    'platform_distribution': [],
                    'socket_distribution': []
                }})

            # Get motherboard stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price,
                    COUNT(CASE WHEN motherboard_model_id IS NOT NULL THEN 1 END) as matched_count,
                    COUNT(CASE WHEN motherboard_model_id IS NULL THEN 1 END) as unmatched_count
                FROM listings
                WHERE category = 'motherboard'
            """)
            stats = dict(cursor.fetchone())

            # Distribution by posting year (from listings.date_posted)
            cursor.execute("""
                SELECT
                    EXTRACT(YEAR FROM date_posted)::int AS year,
                    COUNT(*) AS count
                FROM listings
                WHERE category = 'motherboard' AND is_active = true AND date_posted IS NOT NULL
                GROUP BY year
                ORDER BY year
            """)
            year_distribution = [convert_decimal_to_float(dict(row)) for row in cursor.fetchall()]

            # Platform (Intel/AMD/Other) distribution based on socket
            cursor.execute("""
                SELECT
                    CASE
                        WHEN m.socket ILIKE 'LGA%%' THEN 'Intel'
                        WHEN m.socket ILIKE 'AM%%' OR m.socket ILIKE 'FM%%' OR m.socket ILIKE 'STR%%' THEN 'AMD'
                        ELSE 'Other'
                    END AS platform,
                    COUNT(*) AS count
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true
                GROUP BY platform
                ORDER BY count DESC
            """)
            platform_distribution = [dict(row) for row in cursor.fetchall()]

            # Socket distribution
            cursor.execute("""
                SELECT
                    m.socket,
                    COUNT(*) AS count
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true AND m.socket IS NOT NULL
                GROUP BY m.socket
                ORDER BY count DESC
            """)
            socket_distribution = [dict(row) for row in cursor.fetchall()]

            stats['year_distribution'] = year_distribution
            stats['platform_distribution'] = platform_distribution
            stats['socket_distribution'] = socket_distribution

            cursor.close()

            # Convert Decimal to float for JSON serialization
            stats = convert_decimal_to_float(stats)

            return jsonify({'success': True, 'stats': stats})

        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motherboard-models')
@cache_control(max_age=30)
def get_motherboard_models():
    """Get motherboard model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if motherboard_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

            cursor.execute(f"""
                SELECT
                    m.id,
                    m.brand,
                    m.model,
                    m.socket,
                    m.chipset,
                    m.form_factor,
                    COUNT(l.listing_id) as active_listings,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM motherboard_models m
                JOIN listings l ON m.id = l.motherboard_model_id
                WHERE l.category = 'motherboard'
                    {time_clause}
                    {flagged_clause}
                GROUP BY m.id, m.brand, m.model, m.socket, m.chipset, m.form_factor
                ORDER BY avg_price DESC
            """)

            models = cursor.fetchall()
            cursor.close()

            return jsonify([convert_decimal_to_float(dict(row)) for row in models])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500



@app.route('/api/motherboard-socket-stats')
@cache_control(max_age=30)
def get_motherboard_socket_stats():
    """Get per-socket motherboard and CPU listing statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Motherboard counts per socket
            cursor.execute("""
                SELECT
                    m.socket,
                    COUNT(DISTINCT m.id) as model_count,
                    COUNT(l.listing_id) as motherboard_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM motherboard_models m
                JOIN listings l ON m.id = l.motherboard_model_id
                WHERE l.category = 'motherboard'
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                GROUP BY m.socket
                HAVING COUNT(l.listing_id) > 0
            """)
            mb_rows = cursor.fetchall()
            mb_by_socket = {row['socket']: dict(row) for row in mb_rows}

            # CPU listing counts per socket
            cursor.execute("""
                SELECT
                    c.socket,
                    COUNT(l.listing_id) as cpu_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_cpu_price
                FROM listings l
                JOIN cpu_reference c ON l.matched_cpu_id = c.id
                WHERE l.category = 'cpu'
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                    AND c.socket IS NOT NULL
                GROUP BY c.socket
                HAVING COUNT(l.listing_id) > 0
            """)
            cpu_rows = cursor.fetchall()

            result = []
            for socket, mb in mb_by_socket.items():
                cpu_match = next((r for r in cpu_rows if r['socket'] == socket), None)
                result.append({
                    'socket': socket,
                    'model_count': mb.get('model_count', 0),
                    'motherboard_count': mb.get('motherboard_count', 0),
                    'avg_price': convert_decimal_to_float(mb.get('avg_price')),
                    'min_price': convert_decimal_to_float(mb.get('min_price')),
                    'max_price': convert_decimal_to_float(mb.get('max_price')),
                    'cpu_count': cpu_match['cpu_count'] if cpu_match else 0,
                    'avg_cpu_price': convert_decimal_to_float(cpu_match['avg_cpu_price']) if cpu_match else None,
                })

            # Include sockets that only have CPUs if desired (skip for now to keep chart focused)
            cpu_only_sockets = [r for r in cpu_rows if r['socket'] not in mb_by_socket]
            for cpu in cpu_only_sockets:
                result.append({
                    'socket': cpu['socket'],
                    'model_count': 0,
                    'motherboard_count': 0,
                    'avg_price': None,
                    'min_price': None,
                    'max_price': None,
                    'cpu_count': cpu['cpu_count'],
                    'avg_cpu_price': convert_decimal_to_float(cpu['avg_cpu_price']),
                })

            cursor.close()
            return jsonify(result)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/motherboard-chipsets')
@cache_control(max_age=30)
def get_motherboard_chipsets():
    """Get chipset popularity statistics for motherboard listings."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if motherboard_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            cursor.execute("""
                SELECT
                    m.chipset,
                    m.socket,
                    ARRAY_AGG(DISTINCT m.brand) FILTER (WHERE m.brand IS NOT NULL) as brands,
                    m.form_factor,
                    COUNT(DISTINCT m.id) as model_count,
                    COUNT(l.listing_id) as active_listings,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM motherboard_models m
                JOIN listings l ON m.id = l.motherboard_model_id
                WHERE l.category = 'motherboard'
                    AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                GROUP BY m.chipset, m.socket, m.form_factor
                HAVING COUNT(l.listing_id) > 0
                ORDER BY active_listings DESC
            """)

            chipsets = cursor.fetchall()
            cursor.close()

            # Convert to dict and format brands
            result = []
            for row in chipsets:
                row_dict = dict(row)
                if row_dict.get('brands'):
                    if isinstance(row_dict['brands'], list):
                        row_dict['brands'] = ', '.join(row_dict['brands'])
                result.append(row_dict)

            return jsonify(result)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/motherboard-sockets')
@cache_control(max_age=30)
def get_motherboard_sockets():
    """Get unique sockets from motherboard_reference."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            # Check if motherboard_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result[0] if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            # Get unique sockets from motherboard_models
            cursor.execute("""
                SELECT DISTINCT socket
                FROM motherboard_models
                WHERE socket IS NOT NULL AND socket != ''
                ORDER BY socket
            """)

            sockets = [row[0] for row in cursor.fetchall()]
            cursor.close()

            return jsonify(sockets)

        except Exception as e:
            cursor.close()
            return jsonify([])


@app.route('/api/motherboards/socket-market')
@cache_control(max_age=30)
def get_motherboard_socket_market():
    """Aggregate market stats for a specific socket.

    Query params:
        socket: required, e.g. "LGA1155"
        active: "true"/"false" (default true)
        cpu: optional CPU id — when provided, filter chipsets to those
             compatible with the CPU's generation. This fixes Bug 18
             where searching for i7-6700 (6th gen / Skylake) would
             return H310/B360 (300-series / Coffee Lake ONLY) motherboards
             alongside the actually-compatible H110/B150 (100-series).

    Returns:
        {socket, listing_count, avg_price, min_price, max_price,
         sample_models: [{brand, model, price_eur, listing_id}], ...}
    """
    socket = request.args.get('socket', '').strip()
    if not socket:
        return jsonify({'error': 'socket is required'}), 400
    active = request.args.get('active', 'true').lower() == 'true'
    cpu_id = request.args.get('cpu', '').strip()

    # Bug 18: derive a chipset filter from the CPU's generation, so that
    # LGA 1151 searches for Skylake (gen 6/7) don't return Coffee Lake
    # (gen 8/9) chipsets that share the same physical socket but are
    # electrically incompatible.
    chipset_filter = None
    cpu_generation = None
    if cpu_id:
        with get_db_connection() as conn2:
            cur2 = conn2.cursor(cursor_factory=RealDictCursor)
            try:
                cur2.execute("""SELECT processor_number, cpu_name FROM cpu_reference WHERE id = %s""", (cpu_id,))
                cpu_row = cur2.fetchone()
                if cpu_row:
                    proc_num = (cpu_row.get('processor_number') or '').strip()
                    # The first digit of Intel's 4-digit processor number is
                    # the generation. e.g. i7-6700 → 6, i7-8700 → 8.
                    import re as _re
                    m = _re.search(r'-?(\d)\d{3}', proc_num) or _re.search(r'(\d)\d{3}', cpu_row.get('cpu_name', '') or '')
                    if m:
                        cpu_generation = int(m.group(1))
            finally:
                cur2.close()
        if cpu_generation in (6, 7) and socket in ('LGA1151', 'LGA 1151'):
            chipset_filter = ['H110', 'B150', 'H170', 'Q170', 'Z170']  # 100-series only
        elif cpu_generation in (8, 9) and socket in ('LGA1151', 'LGA 1151'):
            chipset_filter = ['H310', 'B360', 'H370', 'Q370', 'Z370', 'B365', 'Z390']  # 300-series only
        # Other generations / sockets: no filter (all chipsets compatible)

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            where = ["l.category = 'motherboard'",
                     "l.motherboard_model_id IS NOT NULL",
                     "m.socket = %s"]
            params = [socket]
            if active:
                where.append("l.is_active = true")
            if chipset_filter:
                where.append("m.chipset = ANY(%s)")
                params.append(chipset_filter)
            where_sql = " AND ".join(where)

            # Aggregate stats from joined motherboards + listings
            cursor.execute(f"""
                SELECT
                    COUNT(*) AS listing_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price,
                    MIN(l.price_eur) AS min_price,
                    MAX(l.price_eur) AS max_price
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE {where_sql}
            """, params)
            agg = cursor.fetchone() or {'listing_count': 0}

            # Sample (up to 5) representative models for this socket
            cursor.execute(f"""
                SELECT
                    l.listing_id, m.brand, m.model AS motherboard_model, l.price_eur,
                    m.socket, m.chipset, m.form_factor, l.image_url, l.listing_url
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE {where_sql}
                ORDER BY l.price_eur ASC
                LIMIT 5
            """, params)
            sample = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            cursor.close()
            return jsonify({
                'socket': socket,
                'cpu_id': int(cpu_id) if cpu_id else None,
                'cpu_generation': cpu_generation,
                'chipset_filter': chipset_filter,
                'listing_count': int(agg.get('listing_count') or 0),
                'avg_price': float(agg.get('avg_price') or 0) if agg.get('avg_price') else None,
                'min_price': float(agg.get('min_price') or 0) if agg.get('min_price') else None,
                'max_price': float(agg.get('max_price') or 0) if agg.get('max_price') else None,
                'sample_models': sample,
            })
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return jsonify({'error': str(e)}), 500


@app.route('/api/motherboards/cpu-socket-lookup')
@cache_control(max_age=300)
def get_cpu_socket_lookup():
    """Look up the socket for a given CPU name.

    Query params:
        name: CPU name substring (case-insensitive)
        id:   CPU id (optional, takes precedence if both provided)
        limit: max results (default 10)

    Returns:
        {matches: [{id, brand, cpu_name, socket, cores, threads, tdp_w}, ...]}
    """
    cpu_id = request.args.get('id', '').strip()
    name = request.args.get('name', '').strip()
    limit = int(request.args.get('limit', 10))

    if not cpu_id and not name:
        return jsonify({'matches': [], 'error': 'cpu id or name required'}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if cpu_id:
                cursor.execute("""
                    SELECT id, producer AS brand, cpu_name AS model, socket,
                           cores, threads, tdp_w
                    FROM cpu_reference
                    WHERE id = %s
                """, (cpu_id,))
            else:
                cursor.execute("""
                    SELECT id, producer AS brand, cpu_name AS model, socket,
                           cores, threads, tdp_w
                    FROM cpu_reference
                    WHERE socket IS NOT NULL
                      AND (LOWER(cpu_name) LIKE %s
                           OR LOWER(processor_number) LIKE %s
                           OR LOWER(normalized_name) LIKE %s)
                    ORDER BY
                        CASE WHEN LOWER(cpu_name) = LOWER(%s) THEN 0 ELSE 1 END,
                        year_released DESC NULLS LAST,
                        cpu_name
                    LIMIT %s
                """, (f"%{name.lower()}%", f"%{name.lower()}%",
                      f"%{name.lower()}%", name, limit))
            matches = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]
            cursor.close()
            return jsonify({'matches': matches})
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return jsonify({'matches': [], 'error': str(e)}), 500


@app.route('/api/motherboards/lookup')
@cache_control(max_age=120)
def get_motherboard_lookup():
    """Three-level fallback for the computers-page "Detected Components"
    motherboard deep-link.

    Input:  ?model=MSI+PRO+H610M-E  (the scraped model name)
    Output: {level, url, label, count, hint} where `level` is the
    fallback tier the user landed on (model / chipset / socket / none).

    Tries, in order:
      1. exact motherboard model: a motherboard_models row whose
         brand+model match the input AND has at least one active listing
         → /motherboards?model=<x>
      2. chipset fallback: extract a chipset token (e.g. "H610", "B550",
         "X670E") from the input and look up listings by chipset
         → /motherboards?chipset=H610
      3. socket fallback: map the chipset to a known socket
         (LGA1700, AM5, AM4, …) and look up listings by socket
         → /motherboards?socket=LGA1700

    The frontend opens the returned URL in a new tab so the user always
    lands on a non-empty motherboards page even when the exact model is
    out of stock or never scraped.
    """
    import re as _re

    model_input = (request.args.get('model') or '').strip()
    if not model_input:
        return jsonify({'level': 'none', 'url': '/motherboards', 'label': 'All motherboards', 'count': 0, 'hint': 'No model provided'}), 400

    # Normalize: collapse runs of spaces, drop the brand prefix when
    # it's already part of the model (e.g. "MSI PRO H610M-E" → "PRO H610M-E"
    # for the model field; we still pass the full string to the brand ILIKE).
    full = model_input
    cleaned = _re.sub(r'\s+', ' ', full).strip()

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # --- Level 1: exact model match ---
            # Try to find a motherboard_models row whose brand+model ILIKE-matches
            # the input AND has at least one active unflagged listing.
            cursor.execute("""
                SELECT m.id, m.brand, m.model, m.socket, m.chipset,
                       COUNT(l.listing_id) AS listing_count
                FROM motherboard_models m
                LEFT JOIN listings l
                       ON l.motherboard_model_id = m.id
                      AND l.is_active = true
                      AND l.category = 'motherboard'
                      AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                WHERE (m.brand || ' ' || m.model) ILIKE %s
                   OR m.model ILIKE %s
                GROUP BY m.id, m.brand, m.model, m.socket, m.chipset
                HAVING COUNT(l.listing_id) > 0
                ORDER BY
                    CASE WHEN LOWER(m.brand || ' ' || m.model) = LOWER(%s) THEN 0 ELSE 1 END,
                    listing_count DESC
                LIMIT 1
            """, (f'%{cleaned}%', f'%{cleaned}%', cleaned))
            row = cursor.fetchone()
            if row:
                model_param = encodeURIComponent(row['model']) if False else _quote_plus(row['model'])
                cursor.close()
                return jsonify({
                    'level': 'model',
                    'url': f'/motherboards?model={model_param}',
                    'label': f'{row["brand"]} {row["model"]}',
                    'count': int(row['listing_count'] or 0),
                    'hint': f'{row["listing_count"]} active listings of this exact model',
                })

            # --- Level 2: chipset fallback ---
            # Pull a chipset-shaped token out of the input. Chipsets in the
            # data look like: H610, B550, X670E, Z790, B650, H510, A520, …
            # The token always starts with a letter (chipset family) and
            # is followed by 2-4 digits, optionally with a letter suffix.
            chipset_match = _re.search(r'\b([A-Z]{1,2}\d{2,4}[A-Z]?)\b', cleaned, _re.IGNORECASE)
            chipset = chipset_match.group(1).upper() if chipset_match else None
            if chipset:
                # Chipset values in the DB occasionally include the trailing
                # "M" from the model name (e.g. "H61M" instead of "H61"),
                # so we try the full token first and fall back to the
                # stripped version if nothing matches.
                chipset_candidates = [chipset]
                if chipset.endswith('M'):
                    chipset_candidates.append(chipset[:-1])
                for candidate in chipset_candidates:
                    cursor.execute("""
                        SELECT COUNT(*) AS listing_count
                        FROM listings l
                        JOIN motherboard_models m ON l.motherboard_model_id = m.id
                        WHERE m.chipset ILIKE %s
                          AND l.is_active = true
                          AND l.category = 'motherboard'
                          AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                    """, (f'%{candidate}%',))
                    row = cursor.fetchone()
                    count = int(row['listing_count'] or 0) if row else 0
                    if count > 0:
                        cursor.close()
                        return jsonify({
                            'level': 'chipset',
                            'url': f'/motherboards?chipset={_quote_plus(candidate)}',
                            'label': f'All {candidate} motherboards',
                            'count': count,
                            'hint': f'No exact {cleaned!r} in stock — showing {count} {candidate} listings instead',
                        })

            # --- Level 3: socket fallback ---
            # If we still have a CPU socket context (passed in via ?socket=),
            # use that directly. Otherwise map known chipsets to sockets.
            socket_input = (request.args.get('socket') or '').strip()
            socket = None
            if socket_input:
                socket = socket_input
            elif chipset:
                # Curated chipset → socket map for the most common
                # platforms. This is intentionally small — it's a
                # best-effort fallback, not a complete DB lookup.
                chipset_to_socket = {
                    'H610': 'LGA1700', 'B660': 'LGA1700', 'H670': 'LGA1700',
                    'Z690': 'LGA1700', 'B760': 'LGA1700', 'H770': 'LGA1700', 'Z790': 'LGA1700',
                    'H510': 'LGA1200', 'B560': 'LGA1200', 'H570': 'LGA1200',
                    'Z590': 'LGA1200', 'B460': 'LGA1200', 'H470': 'LGA1200', 'Z490': 'LGA1200',
                    'H410': 'LGA1200',
                    'Z390': 'LGA1151', 'Z370': 'LGA1151', 'B360': 'LGA1151',
                    'B365': 'LGA1151', 'H370': 'LGA1151', 'H310': 'LGA1151',
                    'B250': 'LGA1151', 'H270': 'LGA1151', 'Z270': 'LGA1151',
                    'B150': 'LGA1151', 'H170': 'LGA1151', 'Z170': 'LGA1151', 'H110': 'LGA1151',
                    'B550': 'AM4', 'X570': 'AM4', 'A520': 'AM4', 'B450': 'AM4',
                    'X470': 'AM4', 'X370': 'AM4', 'B350': 'AM4', 'A320': 'AM4',
                    'B650': 'AM5', 'X670': 'AM5', 'X670E': 'AM5', 'B650E': 'AM5',
                    'A620': 'AM5',
                    'X399': 'TR4', 'TRX40': 'sTRX4', 'X599': 'sWRX8',
                }
                socket = chipset_to_socket.get(chipset)

            if socket:
                cursor.execute("""
                    SELECT COUNT(*) AS listing_count
                    FROM listings l
                    JOIN motherboard_models m ON l.motherboard_model_id = m.id
                    WHERE m.socket = %s
                      AND l.is_active = true
                      AND l.category = 'motherboard'
                      AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                """, (socket,))
                row = cursor.fetchone()
                count = int(row['listing_count'] or 0) if row else 0
                if count > 0:
                    cursor.close()
                    return jsonify({
                        'level': 'socket',
                        'url': f'/motherboards?socket={_quote_plus(socket)}',
                        'label': f'All {socket} motherboards',
                        'count': count,
                        'hint': f'No {chipset or cleaned!r} in stock — showing {count} {socket} listings instead',
                    })

            cursor.close()
            return jsonify({
                'level': 'none',
                'url': '/motherboards',
                'label': 'All motherboards',
                'count': 0,
                'hint': f'No match for {cleaned!r} — opened the full motherboards page',
            })
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return jsonify({'level': 'none', 'url': '/motherboards', 'label': 'All motherboards', 'count': 0, 'hint': f'lookup error: {e}'}), 500


def _quote_plus(value):
    """Tiny wrapper around urllib.parse.quote_plus for URL param encoding."""
    from urllib.parse import quote_plus
    return quote_plus(str(value), safe='')


@app.route('/api/motherboards/platform-stats')
@cache_control(max_age=30)
def get_motherboard_platform_stats():
    """Get motherboard market stats grouped by year, platform and socket.

    Returns:
        {
          "year_stats": [{"year": 2024, "count": 123, "avg_price": 85.5}, ...],
          "platform_stats": [{"platform": "Intel", "count": 234, "avg_price": 92.1}, ...],
          "socket_stats": [{"socket": "AM4", "count": 111, "avg_price": 70.0}, ...]
        }
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'motherboard_models'
                )
            """)
            table_exists = cursor.fetchone().get('exists', False)

            if not table_exists:
                cursor.close()
                return jsonify({'year_stats': [], 'platform_stats': [], 'socket_stats': []})

            time_filter = request.args.get('time', 'all_time')
            time_clause = ""
            if time_filter == 'week':
                time_clause = "AND l.date_posted > NOW() - INTERVAL '7 days'"
            elif time_filter == 'month':
                time_clause = "AND l.date_posted > NOW() - INTERVAL '30 days'"
            elif time_filter == 'year':
                time_clause = "AND l.date_posted > NOW() - INTERVAL '1 year'"

            # Year distribution
            cursor.execute(f"""
                SELECT
                    EXTRACT(YEAR FROM l.date_posted)::int AS year,
                    COUNT(*) AS count,
                    ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true
                  AND l.motherboard_confidence_score >= 0.70
                  AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                  {time_clause}
                GROUP BY EXTRACT(YEAR FROM l.date_posted)
                HAVING EXTRACT(YEAR FROM l.date_posted) IS NOT NULL
                ORDER BY year DESC
            """)
            year_stats = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # Platform / Socket distribution
            cursor.execute(f"""
                SELECT
                    m.socket,
                    COUNT(*) AS count,
                    ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price
                FROM listings l
                JOIN motherboard_models m ON l.motherboard_model_id = m.id
                WHERE l.category = 'motherboard' AND l.is_active = true
                  AND l.motherboard_confidence_score >= 0.70
                  AND m.socket IS NOT NULL AND m.socket != ''
                  AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
                  {time_clause}
                GROUP BY m.socket
                ORDER BY count DESC
            """)
            socket_rows = cursor.fetchall()

            platform_stats = {'Intel': {'count': 0, 'avg_total': 0.0}, 'AMD': {'count': 0, 'avg_total': 0.0}, 'Other': {'count': 0, 'avg_total': 0.0}}
            socket_stats = []
            for row in socket_rows:
                r = convert_decimal_to_float(dict(row))
                socket = (r.get('socket') or 'Unknown').strip()
                count = int(r.get('count') or 0)
                avg_price = float(r.get('avg_price') or 0)
                socket_stats.append({'socket': socket, 'count': count, 'avg_price': avg_price})

                socket_lower = socket.lower()
                if socket_lower.startswith('lga') or ('intel' in socket_lower and 'socket' in socket_lower):
                    platform = 'Intel'
                elif socket_lower.startswith('am') or socket_lower in ('tr4', 'strx4'):
                    platform = 'AMD'
                else:
                    platform = 'Other'

                platform_stats[platform]['count'] += count
                platform_stats[platform]['avg_total'] += count * avg_price

            platform_stats_list = []
            for platform, data in platform_stats.items():
                total_count = data['count']
                avg_price = round(data['avg_total'] / total_count, 2) if total_count > 0 else 0
                platform_stats_list.append({'platform': platform, 'count': total_count, 'avg_price': avg_price})
            platform_stats_list.sort(key=lambda x: x['count'], reverse=True)

            cursor.close()

            return jsonify({
                'year_stats': year_stats,
                'platform_stats': platform_stats_list,
                'socket_stats': socket_stats
            })

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


# Monitors routes
@app.route('/monitors')
def monitors_page():
    """Monitor listings page."""
    return render_template('monitors.html')


@app.route('/api/monitors')
@cache_control(max_age=30)
def get_monitors():
    """Get monitor listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            size_filter = request.args.get('size', '')
            resolution_filter = request.args.get('resolution', '')
            panel_filter = request.args.get('panel', '')
            time_filter = request.args.get('time', 'all_time')
            min_confidence = float(request.args.get('min_confidence', 0))

            # Check if monitor_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'monitor_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.description,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.image_url,
                    l.listing_url,
                    l.confidence_score,
                    l.monitor_confidence_score,
                    l.local_image_path,
                    l.monitor_model_id,
                    m.brand,
                    m.model,
                    m.size,
                    m.resolution,
                    m.refresh_rate,
                    m.panel_type,
                    m.nits
                FROM listings l
                LEFT JOIN monitor_models m ON l.monitor_model_id = m.id
                WHERE l.category = 'monitor'
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('monitor')
            if min_confidence > 0:
                query += " AND COALESCE(l.monitor_confidence_score, l.confidence_score, 0) >= %s"
                params.append(min_confidence)
            if size_filter:
                query += " AND m.size = %s"
                params.append(float(size_filter))
            if resolution_filter:
                query += " AND m.resolution ILIKE %s"
                params.append(f'%{resolution_filter}%')
            if panel_filter:
                query += " AND m.panel_type ILIKE %s"
                params.append(f'%{panel_filter}%')

            # Refresh rate filter
            refresh_rate_filter = request.args.get('refresh_rate', '')
            if refresh_rate_filter:
                try:
                    query += " AND m.refresh_rate = %s"
                    params.append(int(refresh_rate_filter))
                except ValueError:
                    pass

            query += get_time_filter_sql(time_filter, 'l')

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Compute price stats per monitor model from active listings
            cursor.execute("""
                SELECT
                    l.monitor_model_id,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(*) as listing_count
                FROM listings l
                WHERE l.category = 'monitor' AND l.is_active = true
                  AND l.monitor_model_id IS NOT NULL
                GROUP BY l.monitor_model_id
            """)
            monitor_stats = {}
            for row in cursor.fetchall():
                monitor_stats[row['monitor_model_id']] = convert_decimal_to_float(dict(row))

            # Get timestamps for "new" badge calculation
            cursor.execute("""
                SELECT MAX(first_seen_at) as last_import_time
                FROM listings
                WHERE category = 'monitor'
            """)
            last_import_result = cursor.fetchone()
            last_import_time = last_import_result['last_import_time'] if last_import_result else None

            # Mark listings as new if they were first seen on the most recent calendar day.
            # This matches user expectation that all listings from today's scrape are "new".
            last_import_date = last_import_time.date() if last_import_time else None

            # Enhance listings with price comparison and new flag
            enhanced_listings = []
            for listing in listings:
                listing_dict = convert_decimal_to_float(dict(listing))

                # Add price stats
                if listing_dict.get('monitor_model_id') and listing_dict['monitor_model_id'] in monitor_stats:
                    stats = monitor_stats[listing_dict['monitor_model_id']]
                    listing_dict['price_stats'] = {
                        'avg': stats['avg_price'],
                        'min': stats['min_price'],
                        'max': stats['max_price'],
                        'below_avg': listing_dict['price_eur'] < stats['avg_price'],
                        'percentile': round((listing_dict['price_eur'] - stats['min_price']) /
                                          (stats['max_price'] - stats['min_price']) * 100, 1)
                                          if stats['max_price'] > stats['min_price'] else 50,
                        'listing_count': stats['listing_count']
                    }

                # Mark as new based on latest scrape calendar day
                first_seen = listing_dict.get('first_seen_at')
                if last_import_date and first_seen:
                    listing_dict['is_new'] = (first_seen.date() if hasattr(first_seen, 'date') else first_seen) == last_import_date
                else:
                    listing_dict['is_new'] = False

                enhanced_listings.append(listing_dict)

            cursor.close()

            return jsonify(enhanced_listings)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/monitor-filters')
@cache_control(max_age=30)
def get_monitor_filters():
    """Get filter option values for monitor listings."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if monitor_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'monitor_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify({
                    'sizes': [],
                    'resolutions': [],
                    'refresh_rates': [],
                    'panel_types': [],
                    'locations': []
                })

            # Sizes from monitor_models
            cursor.execute("""
                SELECT DISTINCT m.size
                FROM monitor_models m
                JOIN listings l ON m.id = l.monitor_model_id
                WHERE l.category = 'monitor' AND l.is_active = true AND m.size IS NOT NULL
                ORDER BY m.size
            """)
            sizes = [row['size'] for row in cursor.fetchall()]

            # Resolutions from monitor_models
            cursor.execute("""
                SELECT DISTINCT m.resolution
                FROM monitor_models m
                JOIN listings l ON m.id = l.monitor_model_id
                WHERE l.category = 'monitor' AND l.is_active = true AND m.resolution IS NOT NULL AND m.resolution <> ''
                ORDER BY m.resolution
            """)
            resolutions = [row['resolution'] for row in cursor.fetchall()]

            # Refresh rates from monitor_models
            cursor.execute("""
                SELECT DISTINCT m.refresh_rate
                FROM monitor_models m
                JOIN listings l ON m.id = l.monitor_model_id
                WHERE l.category = 'monitor' AND l.is_active = true AND m.refresh_rate IS NOT NULL
                ORDER BY m.refresh_rate
            """)
            refresh_rates = [row['refresh_rate'] for row in cursor.fetchall()]

            # Panel types from monitor_models
            cursor.execute("""
                SELECT DISTINCT m.panel_type
                FROM monitor_models m
                JOIN listings l ON m.id = l.monitor_model_id
                WHERE l.category = 'monitor' AND l.is_active = true AND m.panel_type IS NOT NULL AND m.panel_type <> ''
                ORDER BY m.panel_type
            """)
            panel_types = [row['panel_type'] for row in cursor.fetchall()]

            # Seller locations from listings
            cursor.execute("""
                SELECT DISTINCT l.seller_location
                FROM listings l
                WHERE l.category = 'monitor' AND l.is_active = true AND l.seller_location IS NOT NULL AND l.seller_location <> ''
                ORDER BY l.seller_location
            """)
            locations = [row['seller_location'] for row in cursor.fetchall()]

            cursor.close()

            return jsonify({
                'sizes': sizes,
                'resolutions': resolutions,
                'refresh_rates': refresh_rates,
                'panel_types': panel_types,
                'locations': locations
            })
        except Exception as e:
            cursor.close()
            return jsonify({
                'sizes': [],
                'resolutions': [],
                'refresh_rates': [],
                'panel_types': [],
                'locations': []
            })


@app.route('/api/monitor-stats')
@cache_control(max_age=30)
def get_monitor_stats():
    """Get monitor performance class statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_filter = request.args.get('time', 'all_time')
            time_clause = get_time_filter_sql(time_filter, 'l')

            # Check if monitor_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'monitor_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify({
                    'success': True,
                    'stats': {
                        'by_performance_class': {},
                        'by_refresh_rate': {},
                        'by_resolution': {},
                        'by_size': {}
                    }
                })

            # Get listings with monitor specs for categorization
            cursor.execute(f"""
                SELECT
                    m.size,
                    m.resolution,
                    m.refresh_rate,
                    m.panel_type,
                    COUNT(*) as count
                FROM listings l
                JOIN monitor_models m ON l.monitor_model_id = m.id
                WHERE l.category = 'monitor'
                {time_clause}
                GROUP BY m.size, m.resolution, m.refresh_rate, m.panel_type
            """)

            rows = cursor.fetchall()

            # Categorize monitors - merge 4K UHD and Professional under "Creator"
            performance_counts = {
                'gaming': 0,
                'ultrawide': 0,
                'creator': 0,  # Merged 4K + Professional
                'office': 0,
                'budget': 0,
                'high-end': 0
            }
            refresh_counts = {}
            resolution_counts = {}
            size_counts = {}

            for row in rows:
                size = int(row['size']) if row['size'] else 0
                resolution = row['resolution'] or ''
                refresh = int(row['refresh_rate']) if row['refresh_rate'] else 60
                panel = row['panel_type'] or ''
                count = row['count']

                # Categorize - merge 4K and Professional under "Creator"
                is_ultrawide = '2560x1080' in resolution or '3440x1440' in resolution or '3840x1600' in resolution or '5120x1440' in resolution or 'ultrawide' in resolution.lower()
                is_4k = '3840x2160' in resolution or '4096x2160' in resolution or '4K' in resolution
                is_professional = panel and ('ips' in panel.lower() or 'oled' in panel.lower() or 'mini-led' in panel.lower())

                if refresh >= 144 and is_4k:
                    performance_counts['high-end'] += count
                elif is_ultrawide:
                    performance_counts['ultrawide'] += count
                elif refresh >= 144:
                    performance_counts['gaming'] += count
                elif is_4k or is_professional:
                    # Merge 4K UHD and Professional under "Creator"
                    performance_counts['creator'] += count
                elif size <= 22 and refresh <= 75:
                    performance_counts['budget'] += count
                else:
                    performance_counts['office'] += count

                # Refresh rate counts
                refresh_counts[refresh] = refresh_counts.get(refresh, 0) + count

                # Resolution counts
                if resolution:
                    resolution_counts[resolution] = resolution_counts.get(resolution, 0) + count

                # Size counts
                size_counts[size] = size_counts.get(size, 0) + count

            cursor.close()

            return jsonify({
                'success': True,
                'stats': {
                    'by_performance_class': performance_counts,
                    'by_refresh_rate': refresh_counts,
                    'by_resolution': resolution_counts,
                    'by_size': size_counts
                }
            })

        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitor-details/<int:monitor_id>')
@cache_control(max_age=30)
def get_monitor_details_by_id(monitor_id):
    """Get monitor reference details by ID (for flagging with model mismatch)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT
                    id,
                    brand,
                    model,
                    size,
                    resolution,
                    refresh_rate,
                    panel_type,
                    normalized_name
                FROM monitor_models
                WHERE id = %s
            """, (monitor_id,))

            monitor = cursor.fetchone()

            if not monitor:
                return jsonify({'success': False, 'error': 'Monitor not found'}), 404

            return jsonify({'success': True, 'monitor': dict(monitor)})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()


@app.route('/api/monitor-models')
@cache_control(max_age=30)
def get_monitor_models():
    """Get monitor model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_filter = request.args.get('time', 'all_time')
            time_clause = get_time_filter_sql(time_filter, 'l')

            # Check if monitor_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'monitor_models'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            cursor.execute(f"""
                SELECT
                    m.id,
                    m.brand,
                    m.model,
                    m.size,
                    m.resolution,
                    m.refresh_rate,
                    m.panel_type,
                    COUNT(l.listing_id) as listing_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM monitor_models m
                JOIN listings l ON m.id = l.monitor_model_id
                WHERE l.category = 'monitor' {time_clause}
                GROUP BY m.id, m.brand, m.model, m.size, m.resolution, m.refresh_rate, m.panel_type
                ORDER BY avg_price DESC
            """)

            models = cursor.fetchall()
            cursor.close()

            # Convert Decimal to float for JSON serialization
            models_dict = [convert_decimal_to_float(dict(row)) for row in models]
            return jsonify(models_dict)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500




@app.route('/api/psus/stats')
@cache_control(max_age=30)
def get_psu_stats():
    """Get PSU statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_filter = request.args.get('time', 'all_time')
            time_clause = get_time_filter_sql(time_filter, 'l')

            # Get basic stats
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings l
                WHERE l.category = 'psu' AND l.is_active = true
                {time_clause}
            """)

            stats = dict(cursor.fetchone())

            # Get wattage distribution for chart
            cursor.execute(f"""
                SELECT
                    p.wattage,
                    COUNT(*) as listing_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                FROM listings l
                LEFT JOIN psu_reference p ON l.matched_psu_id = p.id
                WHERE l.category = 'psu' AND l.is_active = true AND p.wattage IS NOT NULL
                {time_clause}
                GROUP BY p.wattage
                ORDER BY p.wattage ASC
            """)

            wattage_distribution = [convert_decimal_to_float(dict(row)) for row in cursor.fetchall()]
            stats['wattage_distribution'] = wattage_distribution

            # Get efficiency rating distribution
            cursor.execute(f"""
                SELECT
                    p.efficiency_rating,
                    COUNT(*) as listing_count,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price
                FROM listings l
                LEFT JOIN psu_reference p ON l.matched_psu_id = p.id
                WHERE l.category = 'psu' AND l.is_active = true AND p.efficiency_rating IS NOT NULL
                {time_clause}
                GROUP BY p.efficiency_rating
                ORDER BY listing_count DESC
            """)

            efficiency_distribution = [convert_decimal_to_float(dict(row)) for row in cursor.fetchall()]
            stats['efficiency_distribution'] = efficiency_distribution

            cursor.close()

            # Convert Decimal to float for JSON serialization
            stats = convert_decimal_to_float(stats)

            return jsonify({'success': True, 'stats': stats})

        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500

# RAM routes
@app.route('/ram')
def ram_page():
    """RAM listings page."""
    return render_template('ram.html')


@app.route('/ram-simple')
def ram_simple_page():
    """Simple RAM listings page for debugging."""
    return render_template('ram_simple.html')


@app.route('/api/rams')
@cache_control(max_age=30)
def get_ram():
    """Get RAM listings with filters."""
    cursor = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            show_active = request.args.get('active', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            capacity_filter = request.args.get('capacity', '')
            type_filter = request.args.get('type', '') or request.args.get('ddr_type', '')
            speed_filter = request.args.get('speed', '')
            time_filter = request.args.get('time', 'all_time')
            min_confidence = float(request.args.get('min_confidence', 0))
            ram_id_filter = request.args.get('ram_id', '')

            # Check if ram_reference table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'ram_reference'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            # Get available columns
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ram_reference'
            """)
            columns = {row['column_name'] for row in cursor.fetchall()}

            # Build query based on available columns.
            # The `speed` column is text like "DDR4-3200", not an integer.
            # We extract the trailing 3-5 digit number for numeric filtering,
            # so a `speed=3200` filter matches DDR4-3200 / DDR5-3200 etc.
            speed_column = 'speed_mhz' if 'speed_mhz' in columns else 'speed'
            speed_field = f'r.{speed_column}'
            speed_mhz_sql = (
                f"CAST(NULLIF((regexp_match({speed_field}, '(\\d{{3,5}})'))[1], '') AS INTEGER)"
                if speed_column == 'speed'
                else f'{speed_field}::INTEGER'
            )

            query = f"""
                SELECT
                    l.listing_id,
                    l.title,
                    l.description,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.ram_confidence_score as confidence_score,
                    l.ram_match_method as match_method,
                    r.name as ram_name,
                    r.capacity_gb,
                    r.type as ram_type,
                    r.type as ddr_type,
                    l.matched_ram_id,
                    {speed_field} as speed,
                    r.modules,
                    r.cas_latency,
                    COALESCE(l.date_posted, l.first_seen_at, l.created_at) as date_posted
                FROM listings l
                JOIN ram_reference r ON l.matched_ram_id = r.id
                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                WHERE l.category = 'ram'
                    AND l.matched_ram_id IS NOT NULL
                    AND fl.listing_id IS NULL
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('ram')
            if min_confidence > 0:
                query += " AND COALESCE(l.ram_confidence_score, 0) >= %s"
                params.append(min_confidence)
            if capacity_filter:
                query += " AND r.capacity_gb = %s"
                params.append(int(capacity_filter))
            if type_filter:
                query += " AND r.type ILIKE %s"
                params.append(f'%{type_filter}%')
            if speed_filter:
                # `speed_mode` mirrors the VRAM filter: `min` (default, ≥ selected)
                # or `exact` (only the chosen speed). The user can flip modes via
                # the `<` button on the frontend.
                speed_mode = request.args.get('speed_mode', 'min').lower()
                op = '=' if speed_mode == 'exact' else '>='
                query += f" AND {speed_mhz_sql} {op} %s"
                params.append(int(speed_filter))
            if ram_id_filter:
                try:
                    query += " AND r.id = %s"
                    params.append(int(ram_id_filter))
                except ValueError:
                    pass

            query += get_time_filter_sql(time_filter, 'l')

            sort_column = 'l.price_eur' if sort_by == 'price' else "COALESCE(l.date_posted, l.first_seen_at, l.created_at)"
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir}"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Build market position stats over all unflagged matched RAM listings
            # (same DDR type + capacity), not limited to active-only so comparisons work
            # regardless of the active filter.
            stats_params = []
            stats_where = "WHERE l.category = 'ram'"

            if capacity_filter:
                stats_where += " AND r.capacity_gb = %s"
                stats_params.append(int(capacity_filter))
            if type_filter:
                stats_where += " AND r.type ILIKE %s"
                stats_params.append(f'%{type_filter}%')

            stats_query = f"""
                WITH ram_stats AS (
                    SELECT
                        r.type,
                        r.capacity_gb,
                        COUNT(l.listing_id) as listing_count,
                        AVG(l.price_eur) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price
                    FROM listings l
                    JOIN ram_reference r ON l.matched_ram_id = r.id
                    LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                    {stats_where}
                        AND fl.listing_id IS NULL
                    GROUP BY r.type, r.capacity_gb
                )
                SELECT
                    type,
                    capacity_gb,
                    listing_count,
                    ROUND(avg_price::numeric, 2) as avg_price,
                    min_price,
                    max_price
                FROM ram_stats
            """

            cursor.execute(stats_query, stats_params)

            price_stats_rows = cursor.fetchall()
            price_stats_map = {}
            for row in price_stats_rows:
                key = f"{row['type']}_{row['capacity_gb']}"
                price_stats_map[key] = {
                    'avg': float(row['avg_price']) if row['avg_price'] else 0,
                    'min': float(row['min_price']) if row['min_price'] else 0,
                    'max': float(row['max_price']) if row['max_price'] else 0
                }

            # Build model-specific stats (same matched_ram_id, unflagged, all-time)
            # Also track how many listings exist per matched_ram_id to identify unicorns
            model_stats_query = """
                SELECT
                    l.matched_ram_id,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(l.listing_id) as listing_count
                FROM listings l
                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                WHERE l.category = 'ram'
                  AND l.matched_ram_id IS NOT NULL
                  AND fl.listing_id IS NULL
                GROUP BY l.matched_ram_id
            """
            cursor.execute(model_stats_query)
            model_stats_rows = cursor.fetchall()
            model_stats_map = {}
            for row in model_stats_rows:
                model_stats_map[row['matched_ram_id']] = {
                    'avg': float(row['avg_price']) if row['avg_price'] else 0,
                    'min': float(row['min_price']) if row['min_price'] else 0,
                    'max': float(row['max_price']) if row['max_price'] else 0,
                    'count': int(row['listing_count']) if row['listing_count'] else 0
                }

            result = []
            for row in listings:
                row_dict = dict(row)
                row_dict = convert_decimal_to_float(row_dict)

                # Add model position stats (same matched_ram_id, unflagged, all-time)
                matched_ram_id = row_dict.get('matched_ram_id')
                if matched_ram_id in model_stats_map:
                    stats = model_stats_map[matched_ram_id]
                    current_price = row_dict.get('price_eur', 0)
                    if stats['count'] <= 1:
                        row_dict['is_unicorn'] = True
                        row_dict['price_stats'] = None
                    else:
                        row_dict['is_unicorn'] = False
                        row_dict['price_stats'] = {
                            'avg': stats['avg'],
                            'min': stats['min'],
                            'max': stats['max'],
                            'below_avg': current_price < stats['avg'] if stats['avg'] else False,
                            'percentile': min(100, int((current_price - stats['min']) / (stats['max'] - stats['min']) * 100)) if stats['max'] > stats['min'] else 50
                        }

                # Add market position stats (same DDR type + capacity, unflagged, active)
                ram_type = row_dict.get('ram_type', '')
                capacity = row_dict.get('capacity_gb', 0)
                ddr_stats_key = f"{ram_type}_{capacity}"
                if ddr_stats_key in price_stats_map:
                    market_stats = price_stats_map[ddr_stats_key]
                    current_price = row_dict.get('price_eur', 0)
                    row_dict['ddr_stats'] = {
                        'ddr_type': ram_type,
                        'capacity_gb': capacity,
                        'avg': market_stats['avg'],
                        'min': market_stats['min'],
                        'max': market_stats['max'],
                        'below_avg': current_price < market_stats['avg'] if market_stats['avg'] else False,
                        'percentile': min(100, int((current_price - market_stats['min']) / (market_stats['max'] - market_stats['min']) * 100)) if market_stats['max'] > market_stats['min'] else 50
                    }

                # Mark as new if this listing is from the latest import for RAM category
                row_dict['is_new'] = is_listing_new(row_dict.get('first_seen_at'), 'ram')

                result.append(row_dict)

            cursor.close()
            return jsonify(result)
    except Exception as e:
        if cursor:
            cursor.close()
        return jsonify([]), 500


@app.route('/api/ram-details/<int:ram_id>')
@cache_control(max_age=30)
def get_ram_details(ram_id):
    """Get RAM reference details by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check available columns
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ram_reference'
            """)
            columns = {row['column_name'] for row in cursor.fetchall()}
            speed_column = 'speed_mhz' if 'speed_mhz' in columns else 'speed'

            cursor.execute(f"""
                SELECT
                    r.id,
                    r.name,
                    r.capacity_gb,
                    r.type,
                    r.{speed_column} as speed,
                    r.modules,
                    r.cas_latency
                FROM ram_reference r
                WHERE r.id = %s
            """, (ram_id,))
            ram = cursor.fetchone()

            cursor.close()

            if not ram:
                return jsonify({'success': False, 'error': 'RAM reference not found'}), 404

            return jsonify({'success': True, 'ram': convert_decimal_to_float(dict(ram))})

        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ram-models')
@cache_control(max_age=30)
def get_ram_models():
    """Get RAM model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if ram_reference table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'ram_reference'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            # Get available columns
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ram_reference'
            """)
            columns = {row['column_name'] for row in cursor.fetchall()}

            # Build query based on available columns
            speed_column = 'speed_mhz' if 'speed_mhz' in columns else 'speed'

            use_active_avg = request.args.get('use_active_avg', 'false').lower() == 'true'
            if use_active_avg:
                base_where = "WHERE l.category = 'ram' AND l.is_active = true"
            else:
                base_where = "WHERE l.category = 'ram' AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)"

            cursor.execute(f"""
                WITH ram_stats AS (
                    SELECT
                        r.id,
                        COUNT(l.listing_id) as active_listings,
                        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY l.price_eur) as p10,
                        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY l.price_eur) as p90
                    FROM ram_reference r
                    JOIN listings l ON r.id = l.matched_ram_id
                    {base_where}
                    GROUP BY r.id
                ),
                filtered AS (
                    SELECT
                        l.matched_ram_id,
                        AVG(l.price_eur) as avg_price,
                        MIN(l.price_eur) as min_price,
                        MAX(l.price_eur) as max_price
                    FROM listings l
                    JOIN ram_stats s ON l.matched_ram_id = s.id
                    {base_where}
                      AND (s.active_listings <= 2 OR l.price_eur BETWEEN s.p10 AND s.p90)
                    GROUP BY l.matched_ram_id
                )
                SELECT
                    r.id,
                    r.name,
                    r.capacity_gb,
                    r.type,
                    r.{speed_column} as speed_mhz,
                    r.modules,
                    s.active_listings,
                    ROUND(f.avg_price::numeric, 2) as avg_price,
                    f.min_price,
                    f.max_price
                FROM ram_stats s
                JOIN ram_reference r ON s.id = r.id
                JOIN filtered f ON s.id = f.matched_ram_id
                ORDER BY f.avg_price DESC
            """)

            models = cursor.fetchall()
            cursor.close()

            return jsonify([convert_decimal_to_float(dict(row)) for row in models])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/rams/stats')
@cache_control(max_age=30)
def get_ram_stats():
    """Get RAM statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_listings,
                    ROUND(AVG(price_eur)::numeric, 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings
                WHERE category = 'ram'
            """)
            stats = dict(cursor.fetchone())

            # Per-DDR breakdown
            cursor.execute("""
                SELECT
                    r.type as ddr_type,
                    COUNT(*) as total,
                    COUNT(CASE WHEN l.is_active THEN 1 END) as active,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg,
                    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY l.price_eur))::numeric, 2) as median
                FROM listings l
                JOIN ram_reference r ON l.matched_ram_id = r.id
                WHERE l.category = 'ram'
                  AND l.matched_ram_id IS NOT NULL
                GROUP BY r.type
            """)
            by_ddr_rows = cursor.fetchall()
            by_ddr = {}
            for row in by_ddr_rows:
                ddr = row.get('ddr_type') or 'Unknown'
                by_ddr[ddr] = {
                    'total': int(row.get('total') or 0),
                    'active': int(row.get('active') or 0),
                    'avg': float(row.get('avg') or 0),
                    'median': float(row.get('median') or 0),
                }
            stats['by_ddr'] = by_ddr
            stats['total_active'] = int(stats.get('active_listings') or 0)

            cursor.close()

            # Convert Decimal to float for JSON serialization
            stats = convert_decimal_to_float(stats)

            return jsonify({'success': True, 'stats': stats})

        except Exception as e:
            cursor.close()
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/rams/model-history/<listing_id>')
@cache_control(max_age=30)
def get_ram_model_history(listing_id):
    """Get model history for a specific RAM listing."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get the matched RAM ID for this listing
            cursor.execute("""
                SELECT matched_ram_id FROM listings WHERE listing_id = %s AND category = 'ram'
            """, (listing_id,))
            result = cursor.fetchone()

            if not result or not result['matched_ram_id']:
                cursor.close()
                return jsonify({'previous_listings': []})

            matched_ram_id = result['matched_ram_id']

            # Get previous listings for the same RAM model
            cursor.execute("""
                SELECT listing_id, price_eur, date_posted
                FROM listings
                WHERE matched_ram_id = %s AND category = 'ram'
                AND listing_id != %s
                ORDER BY date_posted DESC
                LIMIT 5
            """, (matched_ram_id, listing_id))

            previous = cursor.fetchall()

            cursor.close()

            return jsonify({'previous_listings': [dict(row) for row in previous]})

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/listing-ram-stats/<listing_id>')
@cache_control(max_age=30)
def get_listing_ram_stats(listing_id):
    """Return RAM-specific stats for a single listing:
    - exact model: avg / min / max / count of all listings for the same matched_ram_id
    - similar speed: avg/min/max for listings with the same speed (e.g. all DDR4-3200)
    - similar capacity: avg/min/max for listings with the same DDR+capacity
    - exact model history: recent price snapshots for the same matched_ram_id
    - speed_mhz + cas_latency (the popup needs these for the latency calc)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # 1. Pull the listing + its RAM reference (speed, cas, capacity, type, name)
            cursor.execute("""
                SELECT
                    l.listing_id,
                    l.price_eur,
                    l.matched_ram_id,
                    r.name AS ram_name,
                    r.capacity_gb,
                    r.type AS ddr_type,
                    r.speed AS speed_raw,
                    r.modules,
                    r.cas_latency
                FROM listings l
                LEFT JOIN ram_reference r ON l.matched_ram_id = r.id
                WHERE l.listing_id = %s AND l.category = 'ram'
            """, (listing_id,))
            listing = cursor.fetchone()
            if not listing or not listing.get('matched_ram_id'):
                cursor.close()
                return jsonify({'error': 'Listing not found or not matched to a RAM model'}), 404

            matched_ram_id = listing['matched_ram_id']
            ram_name = listing.get('ram_name')
            capacity = listing.get('capacity_gb')
            ddr_type = listing.get('ddr_type')
            speed_raw = listing.get('speed_raw')
            cas_latency = listing.get('cas_latency')

            # 2. Exact model — same matched_ram_id
            cursor.execute("""
                SELECT
                    COUNT(*) AS count,
                    ROUND(AVG(price_eur)::numeric, 2) AS avg,
                    MIN(price_eur) AS min,
                    MAX(price_eur) AS max
                FROM listings
                WHERE category = 'ram' AND matched_ram_id = %s
            """, (matched_ram_id,))
            exact_model = cursor.fetchone() or {}

            # 3. Exact model history — most recent N price snapshots (using listings table
            # since the dedicated price_history table may be empty for many listings)
            cursor.execute("""
                SELECT
                    listing_id,
                    price_eur,
                    date_posted,
                    first_seen_at
                FROM listings
                WHERE category = 'ram' AND matched_ram_id = %s
                ORDER BY COALESCE(date_posted, first_seen_at) DESC NULLS LAST
                LIMIT 12
            """, (matched_ram_id,))
            exact_model_history = [dict(r) for r in cursor.fetchall()]

            # 4. Similar speed — same speed string (e.g. "DDR4-3200")
            similar_speed = None
            if speed_raw:
                cursor.execute("""
                    SELECT
                        COUNT(*) AS count,
                        ROUND(AVG(l.price_eur)::numeric, 2) AS avg,
                        MIN(l.price_eur) AS min,
                        MAX(l.price_eur) AS max
                    FROM listings l
                    JOIN ram_reference r ON l.matched_ram_id = r.id
                    WHERE l.category = 'ram'
                      AND r.speed = %s
                      AND l.matched_ram_id != %s
                """, (speed_raw, matched_ram_id))
                similar_speed = dict(cursor.fetchone() or {})

            # 5. Similar capacity — same DDR type + capacity, different model
            similar_capacity = None
            if ddr_type and capacity:
                cursor.execute("""
                    SELECT
                        COUNT(*) AS count,
                        ROUND(AVG(l.price_eur)::numeric, 2) AS avg,
                        MIN(l.price_eur) AS min,
                        MAX(l.price_eur) AS max
                    FROM listings l
                    JOIN ram_reference r ON l.matched_ram_id = r.id
                    WHERE l.category = 'ram'
                      AND r.type = %s AND r.capacity_gb = %s
                      AND l.matched_ram_id != %s
                """, (ddr_type, capacity, matched_ram_id))
                similar_capacity = dict(cursor.fetchone() or {})

            cursor.close()

            return jsonify({
                'listing': {
                    'listing_id': listing['listing_id'],
                    'price_eur': float(listing['price_eur']) if listing['price_eur'] is not None else None,
                    'ram_name': ram_name,
                    'capacity_gb': capacity,
                    'ddr_type': ddr_type,
                    'speed': speed_raw,
                    'modules': listing.get('modules'),
                    'cas_latency': cas_latency,
                },
                'exact_model': {
                    'count': int(exact_model.get('count') or 0),
                    'avg': float(exact_model['avg']) if exact_model.get('avg') is not None else None,
                    'min': float(exact_model['min']) if exact_model.get('min') is not None else None,
                    'max': float(exact_model['max']) if exact_model.get('max') is not None else None,
                },
                'exact_model_history': exact_model_history,
                'similar_speed': similar_speed and {
                    'count': int(similar_speed.get('count') or 0),
                    'avg': float(similar_speed['avg']) if similar_speed.get('avg') is not None else None,
                    'min': float(similar_speed['min']) if similar_speed.get('min') is not None else None,
                    'max': float(similar_speed['max']) if similar_speed.get('max') is not None else None,
                },
                'similar_capacity': similar_capacity and {
                    'count': int(similar_capacity.get('count') or 0),
                    'avg': float(similar_capacity['avg']) if similar_capacity.get('avg') is not None else None,
                    'min': float(similar_capacity['min']) if similar_capacity.get('min') is not None else None,
                    'max': float(similar_capacity['max']) if similar_capacity.get('max') is not None else None,
                },
            })
        except Exception as e:
            try: cursor.close()
            except: pass
            import traceback; traceback.print_exc()
            return jsonify({'error': str(e)}), 500


# PSUs routes
@app.route('/psu')
@app.route('/psus')
def psus_page():
    """PSU listings page."""
    return render_template('psu.html')


@app.route('/api/psus')
@cache_control(max_age=30)
def get_psus():
    """Get PSU listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('min_confidence', 0))
            time_filter = request.args.get('time', 'all_time')
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            wattage_filter = request.args.get('wattage', '')
            wattage_mode = request.args.get('wattage_mode', 'exact').lower()

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.created_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.psu_confidence_score,
                    l.psu_match_method,
                    l.matched_psu_id,
                    p.name as psu_name,
                    p.wattage as psu_wattage,
                    p.efficiency_rating,
                    p.modular
                FROM listings l
                LEFT JOIN psu_reference p ON l.matched_psu_id = p.id
                WHERE l.category = 'psu'
            """

            params = []
            if show_active:
                query += " AND l.is_active = true"
            query += _unmatched_filter_sql('psu')
            if min_confidence > 0:
                query += " AND l.psu_confidence_score >= %s"
                params.append(min_confidence)
            if wattage_filter:
                if wattage_mode == 'min':
                    query += " AND p.wattage >= %s"
                else:
                    query += " AND p.wattage = %s"
                params.append(int(wattage_filter))

            # Add time filter
            query += get_time_filter_sql(time_filter)

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Add price statistics for each PSU model
            psu_stats = {}
            cursor.execute("""
                SELECT
                    p.id,
                    p.name,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(*) as listing_count
                FROM listings l
                JOIN psu_reference p ON l.matched_psu_id = p.id
                WHERE l.category = 'psu' AND l.is_active = true
                GROUP BY p.id, p.name
                HAVING COUNT(*) >= 2
            """)
            for row in cursor.fetchall():
                psu_stats[row['id']] = convert_decimal_to_float(dict(row))

            # Get timestamps for "new" badge calculation
            cursor.execute("""
                SELECT MAX(first_seen_at) as last_import_time
                FROM listings
                WHERE category = 'psu'
            """)
            last_import_result = cursor.fetchone()
            last_import_time = last_import_result['last_import_time'] if last_import_result else None

            cursor.execute("""
                SELECT DISTINCT first_seen_at
                FROM listings
                WHERE category = 'psu' AND first_seen_at < %s
                ORDER BY first_seen_at DESC
                LIMIT 1
            """, (last_import_time,))
            prev_import_result = cursor.fetchone()
            previous_import_time = prev_import_result['first_seen_at'] if prev_import_result else None

            # Enhance listings with price comparison
            enhanced_listings = []
            for listing in listings:
                listing_dict = convert_decimal_to_float(dict(listing))

                # Hide Andele location
                if listing_dict.get('seller_location', '').lower() == 'andele':
                    listing_dict['seller_location'] = 'X'

                # Add price stats
                if listing_dict.get('matched_psu_id') and listing_dict['matched_psu_id'] in psu_stats:
                    stats = psu_stats[listing_dict['matched_psu_id']]
                    listing_dict['price_stats'] = {
                        'avg': stats['avg_price'],
                        'min': stats['min_price'],
                        'max': stats['max_price'],
                        'below_avg': listing_dict['price_eur'] < stats['avg_price'],
                        'percentile': round((listing_dict['price_eur'] - stats['min_price']) /
                                          (stats['max_price'] - stats['min_price']) * 100, 1)
                                          if stats['max_price'] > stats['min_price'] else 50,
                        'listing_count': stats['listing_count']
                    }

                # Mark as new
                if last_import_time and listing_dict.get('first_seen_at'):
                    if previous_import_time:
                        listing_dict['is_new'] = listing_dict['first_seen_at'] > previous_import_time
                    else:
                        time_diff = (last_import_time - listing_dict['first_seen_at']).total_seconds()
                        listing_dict['is_new'] = time_diff < 86400
                else:
                    listing_dict['is_new'] = False

                enhanced_listings.append(listing_dict)

            cursor.close()

            return jsonify(enhanced_listings)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/psu-models')
@cache_control(max_age=30)
def get_psu_models():
    """Get PSU model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

            cursor.execute(f"""
                SELECT
                    p.id,
                    p.name,
                    p.wattage,
                    p.efficiency_rating,
                    p.modular,
                    COUNT(l.listing_id) as active_listings,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM psu_reference p
                JOIN listings l ON p.id = l.matched_psu_id
                WHERE l.category = 'psu'
                    {time_clause}
                    {flagged_clause}
                GROUP BY p.id, p.name, p.wattage, p.efficiency_rating, p.modular
                ORDER BY avg_price DESC
            """)

            models = cursor.fetchall()
            cursor.close()

            return jsonify([convert_decimal_to_float(dict(row)) for row in models])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500




# Laptops routes
@app.route('/laptops')
def laptops_page():
    """Laptops listings page."""
    return render_template('laptops.html')


@app.route('/api/laptops')
@cache_control(max_age=30)
def get_laptops():
    """Get laptop listings with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            show_active = request.args.get('active', 'true').lower() == 'true'
            exclude_flagged = request.args.get('exclude_flagged', 'true').lower() == 'true'
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')
            time_filter = request.args.get('time', 'all_time')
            brand_filter = request.args.get('brand', '').strip()
            cpu_filter_list = request.args.getlist('cpu')
            cpu_ref_filter_list = request.args.getlist('cpu_ref_id')
            gpu_filter = request.args.get('gpu', '').strip()
            min_price = request.args.get('min_price', '')
            max_price = request.args.get('max_price', '')
            ram_min = request.args.get('ram_min', '')
            ram_max = request.args.get('ram_max', '')
            storage_min = request.args.get('storage_min', '')
            storage_max = request.args.get('storage_max', '')
            storage_type = request.args.get('storage_type', '').strip()
            display_size = request.args.get('display_size', '').strip()
            display_size_min = request.args.get('display_size_min', '').strip()
            display_size_max = request.args.get('display_size_max', '').strip()
            model_filter = request.args.get('model', '').strip()
            city_filter = request.args.get('city', '').strip()
            exclude_city_filter = request.args.get('exclude_city', '').strip()
            material_filter = request.args.get('material', '').strip().lower()
            refresh_rate_min = request.args.get('refresh_rate_min', '').strip()
            has_touchscreen_filter = request.args.get('has_touchscreen', '').strip().lower()
            has_ethernet_filter = request.args.get('has_ethernet', '').strip().lower()
            include_perekups = request.args.get('include_perekups', 'true').lower() == 'true'
            include_lombards = request.args.get('include_lombards', 'true').lower() == 'true'
            include_macbooks = request.args.get('macbook_only', 'false').lower() == 'true'
            exclude_macbooks = request.args.get('exclude_macbooks', 'false').lower() == 'true'
            limit = request.args.get('limit', '50')
            offset = request.args.get('offset', '0')

            try:
                limit = max(1, min(250, int(limit)))
            except ValueError:
                limit = 50
            try:
                offset = max(0, int(offset))
            except ValueError:
                offset = 0

            # Check if laptop_listings table exists to avoid errors before the scraper lands data
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'laptop_listings'
                )
            """)
            table_exists = cursor.fetchone()['exists']

            if not table_exists:
                cursor.close()
                return jsonify({'listings': [], 'total': 0})

            where_clauses = ["1=1"]
            params = []

            if show_active:
                where_clauses.append("l.is_active = true")
            # _unmatched_filter_sql() returns a fragment like " AND x IS NOT NULL ".
            # We're using a list joined with " AND " — strip the leading "AND "
            # so the joiner doesn't produce a double-AND SQL error.
            _unmatched = _unmatched_filter_sql('laptop').strip()
            if _unmatched.upper().startswith('AND '):
                _unmatched = _unmatched[4:]
            if _unmatched:
                where_clauses.append(_unmatched)
            if exclude_flagged:
                where_clauses.append("NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id AND fl.category = 'laptop')")
            if not include_perekups:
                where_clauses.append("COALESCE(l.seller_type, '') != 'perekups'")
            if not include_lombards:
                where_clauses.append("COALESCE(l.seller_type, '') != 'lombards'")
            if brand_filter and include_macbooks:
                where_clauses.append("((l.brand ILIKE %s) OR (l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s))")
                params.extend([f'%{brand_filter}%', '%apple%', '%macbook%', '%macbook%'])
            elif brand_filter and exclude_macbooks:
                where_clauses.append("l.brand ILIKE %s")
                where_clauses.append("NOT (l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
                params.extend([f'%{brand_filter}%', '%apple%', '%macbook%', '%macbook%'])
            elif brand_filter:
                where_clauses.append("l.brand ILIKE %s")
                params.append(f'%{brand_filter}%')
            elif include_macbooks:
                where_clauses.append("(l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
                params.extend(['%apple%', '%macbook%', '%macbook%'])
            elif exclude_macbooks:
                where_clauses.append("NOT (l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
                params.extend(['%apple%', '%macbook%', '%macbook%'])
            if cpu_filter_list:
                cleaned = [c.strip() for c in cpu_filter_list if c.strip()]
                if cleaned:
                    # Match any CPU substring from the selected values (covers
                    # listings that have a raw but no canonical reference yet).
                    or_clauses = []
                    for val in cleaned:
                        or_clauses.append("l.cpu_raw ILIKE %s")
                        params.append(f'%{val}%')
                    where_clauses.append("(" + " OR ".join(or_clauses) + ")")
            if cpu_ref_filter_list:
                # New path: filter by the canonical CPU FK (e.g. "i7-11400H" id).
                # More accurate than the raw ILIKE above — matches exactly the
                # canonical model, not arbitrary substrings.
                cleaned_ids = [int(c) for c in cpu_ref_filter_list if c.strip().isdigit()]
                if cleaned_ids:
                    where_clauses.append("l.cpu_reference_id = ANY(%s)")
                    params.append(cleaned_ids)
            if gpu_filter:
                where_clauses.append("l.gpu_raw ILIKE %s")
                params.append(f'%{gpu_filter}%')
            if min_price:
                try:
                    where_clauses.append("l.price_eur >= %s")
                    params.append(float(min_price))
                except ValueError:
                    pass
            if max_price:
                try:
                    where_clauses.append("l.price_eur <= %s")
                    params.append(float(max_price))
                except ValueError:
                    pass
            if ram_min:
                try:
                    where_clauses.append("l.ram_gb >= %s")
                    params.append(int(ram_min))
                except ValueError:
                    pass
            if ram_max:
                try:
                    where_clauses.append("l.ram_gb <= %s")
                    params.append(int(ram_max))
                except ValueError:
                    pass

            if storage_min:
                try:
                    where_clauses.append("l.storage_gb >= %s")
                    params.append(int(storage_min))
                except ValueError:
                    pass
            if storage_max:
                try:
                    where_clauses.append("l.storage_gb <= %s")
                    params.append(int(storage_max))
                except ValueError:
                    pass
            if storage_type:
                where_clauses.append("l.storage_type ILIKE %s")
                params.append(f'%{storage_type}%')
            if display_size:
                where_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric = %s")
                params.append(float(display_size))
            if display_size_min:
                try:
                    where_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric >= %s")
                    params.append(float(display_size_min))
                except ValueError:
                    pass
            if display_size_max:
                try:
                    where_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric <= %s")
                    params.append(float(display_size_max))
                except ValueError:
                    pass
            if model_filter:
                where_clauses.append("l.model ILIKE %s")
                params.append(f'%{model_filter}%')

            if city_filter:
                where_clauses.append("l.seller_location = %s")
                params.append(city_filter)

            if exclude_city_filter:
                # Filter OUT a single city. IS DISTINCT FROM keeps listings whose
                # location is unknown (NULL) instead of hiding them.
                where_clauses.append("l.seller_location IS DISTINCT FROM %s")
                params.append(exclude_city_filter)

            # Material filter. The legacy schema constrains material to
            # ('Plastic', 'Metal') via CHECK; 'unknown' means l.material IS NULL.
            if material_filter == 'plastic':
                where_clauses.append("lr.material = 'Plastic'")
            elif material_filter == 'metal':
                where_clauses.append("lr.material = 'Metal'")
            elif material_filter == 'unknown':
                where_clauses.append("lr.material IS NULL")

            if refresh_rate_min:
                try:
                    where_clauses.append("lr.refresh_rate_hz >= %s")
                    params.append(int(refresh_rate_min))
                except ValueError:
                    pass

            if has_touchscreen_filter == 'true':
                where_clauses.append("lr.has_touchscreen = TRUE")
            elif has_touchscreen_filter == 'false':
                where_clauses.append("lr.has_touchscreen = FALSE")

            if has_ethernet_filter == 'true':
                where_clauses.append("lr.has_ethernet = TRUE")
            elif has_ethernet_filter == 'false':
                where_clauses.append("lr.has_ethernet = FALSE")

            if time_filter == '7d':
                where_clauses.append("l.date_posted >= NOW() - INTERVAL '7 days'")
            elif time_filter == '30d':
                where_clauses.append("l.date_posted >= NOW() - INTERVAL '30 days'")

            sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
            sort_dir = 'ASC' if sort_order.lower() == 'asc' else 'DESC'

            count_query = f"""
                SELECT COUNT(*) as total
                FROM laptop_listings l
                LEFT JOIN laptop_reference lr ON lr.id = l.laptop_reference_id
                WHERE {' AND '.join(where_clauses)}
            """
            cursor.execute(count_query, tuple(params))
            total = cursor.fetchone()['total']

            listings_query = f"""
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.created_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.description,
                    l.source,
                    l.brand,
                    l.model,
                    l.display_size,
                    l.cpu_raw,
                    l.ram_gb,
                    l.storage_gb,
                    l.storage_type,
                    l.gpu_raw,
                    l.seller_type,
                    l.condition_state,
                    lr.id AS laptop_ref_id,
                    lr.brand AS laptop_brand,
                    lr.model AS laptop_model,
                    lr.model_number AS laptop_model_number,
                    lr.material,
                    lr.usb_c_count,
                    lr.usb_count,
                    lr.hdmi_count,
                    lr.has_hdmi,
                    lr.has_video_pd_usb_c,
                    lr.has_ethernet,
                    lr.has_touchscreen,
                    lr.refresh_rate_hz,
                    lr.resolution AS laptop_resolution,
                    lr.is_valid AS laptop_ref_valid,
                    lrc.id AS cpu_ref_id,
                    lrc.brand AS cpu_brand_normalized,
                    lrc.model AS cpu_model_normalized
                FROM laptop_listings l
                LEFT JOIN laptop_reference lr ON lr.id = l.laptop_reference_id
                LEFT JOIN laptop_reference_cpu lrc ON lrc.id = l.cpu_reference_id
                WHERE {' AND '.join(where_clauses)}
                ORDER BY {sort_column} {sort_dir}
                LIMIT %s OFFSET %s
            """
            cursor.execute(listings_query, tuple(params) + (limit, offset))
            listings = cursor.fetchall()

            cursor.close()

            return jsonify({
                'listings': [convert_decimal_to_float(dict(row)) for row in listings],
                'total': total
            })

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


# Cases routes
@app.route('/cases')
def cases_page():
    """Cases listings page."""
    return render_template('cases.html')


@app.route('/cases/guide')
def cases_guide_page():
    """Cases type guide — browse PC case form factors with proportional SVG silhouettes."""
    # Per-type counts from the reference table
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT type, COUNT(*) as model_count
            FROM case_reference
            WHERE type IS NOT NULL
            GROUP BY type
            ORDER BY COUNT(*) DESC
        """)
        type_counts = {r['type']: r['model_count'] for r in cursor.fetchall()}
        cursor.close()
        return render_template('case_guide.html', type_counts=type_counts)


@app.route('/api/cases')
@cache_control(max_age=30)
def get_cases():
    """Get case listings with rich filters (mirrors GPU endpoint)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # All filter params
            # active param semantics: 'true' (default) → active only;
            # 'false' → inactive only; 'all' → no active filter at all.
            active_param = request.args.get('active', 'true').lower()
            if active_param == 'all':
                active_filter = None       # no clause added
            elif active_param == 'false':
                active_filter = 'inactive' # only inactive
            else:
                active_filter = 'active'   # default: only active
            sort_by = request.args.get('sort', 'first_seen_at')  # first_seen_at | price | confidence
            sort_order = request.args.get('order', 'desc')
            type_filter = request.args.get('type', '').strip()
            color_filter = request.args.get('color', '').strip()
            side_panel_filter = request.args.get('side_panel', '').strip()
            manufacturer_filter = request.args.get('manufacturer', '').strip()
            location_filter = request.args.get('location', '').strip()
            min_confidence = request.args.get('min_confidence', '').strip()
            min_price = request.args.get('min_price', '').strip()
            max_price = request.args.get('max_price', '').strip()
            search = request.args.get('search', '').strip()
            first_seen_after = request.args.get('first_seen_after', '').strip()
            limit = int(request.args.get('limit', '200'))

            query = """
                SELECT
                    l.listing_id,
                    l.title,
                    l.price_eur,
                    l.seller_location,
                    l.date_posted,
                    l.first_seen_at,
                    l.last_seen_at,
                    l.created_at,
                    l.is_active,
                    l.image_url,
                    l.local_image_path,
                    l.listing_url,
                    l.description,
                    l.source,
                    l.matched_case_id,
                    l.case_confidence_score,
                    l.case_match_method,
                    c.name as case_name,
                    c.type as case_type,
                    c.color as case_color,
                    c.side_panel as case_side_panel,
                    c.power_supply as case_power_supply,
                    c.external_volume as case_volume,
                    c.rating as case_rating
                FROM listings l
                LEFT JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
            """

            params = []
            if active_filter == 'active':
                query += " AND l.is_active = true"
            elif active_filter == 'inactive':
                query += " AND l.is_active = false"
            query += _unmatched_filter_sql('case')
            # active_filter == None → no clause, show everything
            if type_filter:
                query += " AND c.type = %s"
                params.append(type_filter)
            if color_filter:
                query += " AND c.color = %s"
                params.append(color_filter)
            if side_panel_filter:
                query += " AND c.side_panel = %s"
                params.append(side_panel_filter)
            if manufacturer_filter:
                query += " AND c.name ILIKE %s"
                params.append(manufacturer_filter + '%')
            if location_filter:
                query += " AND l.seller_location ILIKE %s"
                params.append('%' + location_filter + '%')
            if min_confidence:
                try:
                    mc = float(min_confidence)
                    query += " AND (l.case_confidence_score IS NULL OR l.case_confidence_score >= %s)"
                    params.append(mc)
                except ValueError:
                    pass
            if min_price:
                try:
                    mp = float(min_price)
                    query += " AND l.price_eur >= %s"
                    params.append(mp)
                except ValueError:
                    pass
            if max_price:
                try:
                    xp = float(max_price)
                    query += " AND l.price_eur <= %s"
                    params.append(xp)
                except ValueError:
                    pass
            if search:
                query += " AND (l.title ILIKE %s OR c.name ILIKE %s)"
                params.extend([f'%{search}%', f'%{search}%'])
            if first_seen_after:
                query += " AND l.first_seen_at >= %s"
                params.append(first_seen_after)

            # Sort
            sort_map = {
                'price': 'l.price_eur',
                'first_seen_at': 'l.first_seen_at',
                'date_posted': 'l.date_posted',
                'confidence': 'l.case_confidence_score',
            }
            sort_column = sort_map.get(sort_by, 'l.first_seen_at')
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
            # NULLS LAST for confidence to keep high-confidence on top
            if sort_by == 'confidence':
                query += f" ORDER BY {sort_column} {sort_dir} NULLS LAST"
            else:
                query += f" ORDER BY {sort_column} {sort_dir} NULLS LAST"
            query += f" LIMIT {limit}"

            cursor.execute(query, params)
            listings = cursor.fetchall()

            # Price stats per case model (across all listings, not just active)
            case_stats = {}
            cursor.execute("""
                SELECT
                    c.id,
                    c.name,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price,
                    COUNT(*) as listing_count
                FROM listings l
                JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
                GROUP BY c.id, c.name
                HAVING COUNT(*) >= 1
            """)
            for row in cursor.fetchall():
                case_stats[row['id']] = dict(row)

            # "is_new" badge via last import time
            cursor.execute("""
                SELECT MAX(first_seen_at) as last_import_time
                FROM listings
                WHERE category = 'case'
            """)
            last_import_time = (cursor.fetchone() or {}).get('last_import_time')

            cursor.execute("""
                SELECT MAX(first_seen_at) as prev_import_time
                FROM listings
                WHERE category = 'case' AND first_seen_at < %s
            """, (last_import_time,)) if last_import_time else None
            previous_import_time = None
            try:
                previous_import_time = (cursor.fetchone() or {}).get('prev_import_time')
            except Exception:
                previous_import_time = None

            enhanced_listings = []
            for listing in listings:
                listing_dict = convert_decimal_to_float(dict(listing))

                if (listing_dict.get('seller_location') or '').lower() == 'andele':
                    listing_dict['seller_location'] = 'X'

                # Price stats (for avg/deal badge/percentile) — convert stats to float
                mid = listing_dict.get('matched_case_id')
                if mid and mid in case_stats:
                    stats = case_stats[mid]
                    avg_f = float(stats['avg_price']) if stats['avg_price'] is not None else None
                    min_f = float(stats['min_price']) if stats['min_price'] is not None else None
                    max_f = float(stats['max_price']) if stats['max_price'] is not None else None
                    price_f = float(listing_dict['price_eur']) if listing_dict.get('price_eur') is not None else None
                    ps = {
                        'avg': avg_f,
                        'min': min_f,
                        'max': max_f,
                        'below_avg': (price_f is not None and avg_f is not None and price_f < avg_f),
                        'listing_count': stats['listing_count'],
                    }
                    if min_f is not None and max_f is not None and price_f is not None and max_f > min_f:
                        ps['percentile'] = round((price_f - min_f) / (max_f - min_f) * 100, 1)
                    else:
                        ps['percentile'] = 50
                    listing_dict['price_stats'] = ps

                # is_new (only attempt when both are proper datetimes)
                try:
                    fs = listing_dict.get('first_seen_at')
                    if last_import_time and fs and hasattr(last_import_time, 'total_seconds') and hasattr(fs, 'total_seconds'):
                        if previous_import_time and hasattr(previous_import_time, 'total_seconds'):
                            listing_dict['is_new'] = fs > previous_import_time
                        else:
                            delta = (last_import_time - fs).total_seconds()
                            listing_dict['is_new'] = delta < 86400
                    else:
                        listing_dict['is_new'] = False
                except Exception:
                    listing_dict['is_new'] = False

                # Derive manufacturer from name
                cn = listing_dict.get('case_name') or ''
                listing_dict['manufacturer'] = cn.split(' ')[0] if cn else ''

                enhanced_listings.append(listing_dict)

            cursor.close()
            return jsonify(enhanced_listings)

        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/case-models')
@cache_control(max_age=30)
def get_case_models():
    """Get case model statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            time_clause, flagged_clause = get_active_avg_clauses(request, 'l')

            cursor.execute(f"""
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.color,
                    COUNT(l.listing_id) as active_listings,
                    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                    MIN(l.price_eur) as min_price,
                    MAX(l.price_eur) as max_price
                FROM case_reference c
                JOIN listings l ON c.id = l.matched_case_id
                WHERE l.category = 'case'
                    {time_clause}
                    {flagged_clause}
                GROUP BY c.id, c.name, c.type, c.color
                ORDER BY avg_price DESC
            """)

            models = cursor.fetchall()
            cursor.close()

            return jsonify([convert_decimal_to_float(dict(row)) for row in models])

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


# ============ Cases — rich data endpoints (mirror GPU page) ============

@app.route('/api/case-stats')
@cache_control(max_age=30)
def get_case_stats():
    """Comprehensive case statistics: totals, by type, by color, by manufacturer, price distribution."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Totals
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_active) AS active,
                    COUNT(*) FILTER (WHERE is_active = false) AS inactive,
                    COUNT(DISTINCT matched_case_id) AS unique_models,
                    ROUND(AVG(price_eur)::numeric, 2) AS avg_price,
                    MIN(price_eur) AS min_price,
                    MAX(price_eur) AS max_price,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_eur)::numeric, 2) AS median_price,
                    COUNT(*) FILTER (WHERE price_eur > 0) AS priced
                FROM listings
                WHERE category = 'case'
            """)
            totals = convert_decimal_to_float(dict(cursor.fetchone()))

            # By type (from case_reference)
            cursor.execute("""
                SELECT COALESCE(c.type, 'Unknown') AS type,
                       COUNT(l.listing_id) AS listings,
                       ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price
                FROM listings l
                LEFT JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
                GROUP BY c.type
                ORDER BY listings DESC
            """)
            by_type = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # By color (from case_reference)
            cursor.execute("""
                SELECT COALESCE(c.color, 'Unknown') AS color,
                       COUNT(l.listing_id) AS listings
                FROM listings l
                LEFT JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
                GROUP BY c.color
                ORDER BY listings DESC
                LIMIT 12
            """)
            by_color = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # By side panel
            cursor.execute("""
                SELECT COALESCE(c.side_panel, 'Unknown') AS side_panel,
                       COUNT(l.listing_id) AS listings
                FROM listings l
                LEFT JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
                GROUP BY c.side_panel
                ORDER BY listings DESC
            """)
            by_side_panel = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # By manufacturer (first word of name)
            cursor.execute("""
                SELECT split_part(COALESCE(c.name, 'Unknown'), ' ', 1) AS manufacturer,
                       COUNT(l.listing_id) AS listings,
                       ROUND(AVG(l.price_eur)::numeric, 2) AS avg_price
                FROM listings l
                LEFT JOIN case_reference c ON l.matched_case_id = c.id
                WHERE l.category = 'case'
                GROUP BY manufacturer
                HAVING COUNT(l.listing_id) >= 1
                ORDER BY listings DESC
                LIMIT 15
            """)
            by_manufacturer = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # Price distribution (price buckets)
            cursor.execute("""
                SELECT
                    CASE
                        WHEN price_eur < 25 THEN '0-25'
                        WHEN price_eur < 50 THEN '25-50'
                        WHEN price_eur < 100 THEN '50-100'
                        WHEN price_eur < 200 THEN '100-200'
                        WHEN price_eur < 400 THEN '200-400'
                        ELSE '400+'
                    END AS bucket,
                    COUNT(*) AS listings
                FROM listings
                WHERE category = 'case' AND price_eur > 0
                GROUP BY bucket
                ORDER BY MIN(price_eur)
            """)
            price_distribution = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # By location
            cursor.execute("""
                SELECT COALESCE(seller_location, 'Unknown') AS location,
                       COUNT(*) AS listings,
                       ROUND(AVG(price_eur)::numeric, 2) AS avg_price
                FROM listings
                WHERE category = 'case'
                GROUP BY seller_location
                ORDER BY listings DESC
                LIMIT 10
            """)
            by_location = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            # Confidence breakdown
            cursor.execute("""
                SELECT
                    CASE
                        WHEN case_confidence_score >= 0.9 THEN 'high'
                        WHEN case_confidence_score >= 0.7 THEN 'medium'
                        WHEN case_confidence_score IS NULL THEN 'unmatched'
                        ELSE 'low'
                    END AS tier,
                    COUNT(*) AS listings
                FROM listings
                WHERE category = 'case'
                GROUP BY tier
                ORDER BY listings DESC
            """)
            confidence_breakdown = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            cursor.close()

            return jsonify({
                'totals': totals,
                'by_type': by_type,
                'by_color': by_color,
                'by_side_panel': by_side_panel,
                'by_manufacturer': by_manufacturer,
                'by_location': by_location,
                'price_distribution': price_distribution,
                'confidence_breakdown': confidence_breakdown,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/case-filters')
@cache_control(max_age=30)
def get_case_filters():
    """Return distinct filter values for the case page."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT DISTINCT type FROM case_reference WHERE type IS NOT NULL ORDER BY type")
            types = [r['type'] for r in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT color FROM case_reference WHERE color IS NOT NULL ORDER BY color")
            colors = [r['color'] for r in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT side_panel FROM case_reference WHERE side_panel IS NOT NULL ORDER BY side_panel")
            side_panels = [r['side_panel'] for r in cursor.fetchall()]

            cursor.execute("""
                SELECT split_part(name, ' ', 1) AS manufacturer, COUNT(*) AS c
                FROM case_reference
                GROUP BY 1
                HAVING COUNT(*) >= 10
                ORDER BY 2 DESC
            """)
            manufacturers = [r['manufacturer'] for r in cursor.fetchall()]

            cursor.close()
            return jsonify({
                'types': types,
                'colors': colors,
                'side_panels': side_panels,
                'manufacturers': manufacturers,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/case-reference/<int:case_id>')
@cache_control(max_age=30)
def get_case_reference(case_id):
    """Get full case reference details by ID (for rich detail modal)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM case_reference WHERE id = %s", (case_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Not found'}), 404

            # All listings for this model
            cursor.execute("""
                SELECT listing_id, title, price_eur, seller_location, date_posted,
                       first_seen_at, last_seen_at, is_active, image_url, local_image_path
                FROM listings
                WHERE category = 'case' AND matched_case_id = %s
                ORDER BY first_seen_at DESC
                LIMIT 50
            """, (case_id,))
            listings = [convert_decimal_to_float(dict(r)) for r in cursor.fetchall()]

            cursor.close()
            return jsonify({
                'reference': convert_decimal_to_float(dict(row)),
                'listings': listings,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/console-models')
@cache_control(max_age=30)
def get_console_models():
    """Get console models with price statistics - using console_listings table."""
    cursor = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if console tables exist
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'console_listings'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([
                    {
                        'console_id': 1,
                        'console_name': 'PlayStation 5',
                        'total_listings': 0,
                        'active_listings': 0,
                        'avg_price': 0,
                        'min_price': 0,
                        'max_price': 0
                    },
                    {
                        'console_id': 2,
                        'console_name': 'Xbox Series X',
                        'total_listings': 0,
                        'active_listings': 0,
                        'avg_price': 0,
                        'min_price': 0,
                        'max_price': 0
                    }
                ])

            # Get console stats from console_listings joined with console_reference
            cursor.execute("""
                SELECT
                    COALESCE(cr.id, 0) as console_id,
                    COALESCE(cr.name, 'Unknown Console') as console_name,
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN cl.is_active THEN 1 END) as active_listings,
                    ROUND(AVG(cl.price_eur)::numeric, 2) as avg_price,
                    MIN(cl.price_eur) as min_price,
                    MAX(cl.price_eur) as max_price
                FROM console_listings cl
                LEFT JOIN console_reference cr ON cl.matched_console_id = cr.id
                GROUP BY cr.id, cr.name
                HAVING COUNT(*) > 0
                ORDER BY cr.name NULLS LAST
                LIMIT 50
            """)

            models = cursor.fetchall()

            if not models or len(models) == 0:
                # Fallback: return sample console data if no consoles found
                cursor.close()
                return jsonify([
                    {
                        'console_id': 1,
                        'console_name': 'PlayStation 5',
                        'total_listings': 0,
                        'active_listings': 0,
                        'avg_price': 0,
                        'min_price': 0,
                        'max_price': 0
                    },
                    {
                        'console_id': 2,
                        'console_name': 'Xbox Series X',
                        'total_listings': 0,
                        'active_listings': 0,
                        'avg_price': 0,
                        'min_price': 0,
                        'max_price': 0
                    }
                ])

            cursor.close()

            return jsonify([convert_decimal_to_float(dict(row)) for row in models])

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify([])
        cursor.close()
        # Return empty array on error
        return jsonify([])


@app.route('/api/consoles')
@cache_control(max_age=30)
def get_consoles():
    """Get console listings with filters and sorting - using console_listings table."""
    cursor = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            show_active = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('min_confidence', 0))
            console_filter = request.args.get('console', 'all')
            sort_by = request.args.get('sort', 'date_posted')
            sort_order = request.args.get('order', 'desc')

            # Check if console_listings table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'console_listings'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            # Build WHERE clauses
            where_clauses = ["1=1"]  # Base condition
            params = []

            if show_active:
                where_clauses.append("cl.is_active = true")
            if min_confidence > 0:
                where_clauses.append("COALESCE(cl.console_confidence_score, 0) >= %s")
                params.append(min_confidence)
            if console_filter != 'all':
                where_clauses.append("cr.name ILIKE %s")
                params.append(f'%{console_filter}%')

            # Add sorting
            sort_column = 'cl.price_eur' if sort_by == 'price' else "COALESCE(cl.date_posted, cl.first_seen_at, cl.last_seen_at, cl.created_at)"
            sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'

            query = f"""
                SELECT
                    cl.listing_id,
                    cl.title,
                    cl.price_eur,
                    cl.seller_location,
                    cl.date_posted,
                    cl.first_seen_at,
                    cl.last_seen_at,
                    cl.created_at,
                    cl.is_active,
                    cl.listing_url,
                    cl.image_url,
                    cl.local_image_path,
                    cl.console_confidence_score,
                    cl.console_match_method,
                    cl.variant_confidence_score,
                    cl.variant_match_method,
                    cl.edition_confidence_score,
                    cl.edition_match_method,
                    cl.is_special_edition,
                    cl.special_edition_note,
                    cl.matched_console_id,
                    cl.matched_variant_id,
                    cl.matched_edition_id,
                    cr.name as console_name,
                    cv.model_name as variant_name,
                    ce.edition_name
                FROM console_listings cl
                LEFT JOIN console_reference cr ON cl.matched_console_id = cr.id
                LEFT JOIN console_variants cv ON cl.matched_variant_id = cv.id
                LEFT JOIN console_editions ce ON cl.matched_edition_id = ce.id
                WHERE {' AND '.join(where_clauses)}
                ORDER BY {sort_column} {sort_dir}
                LIMIT 100
            """

            if params:
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)
            listings = cursor.fetchall()

            # Get flagged listing IDs - check if table exists first
            flagged_ids = set()
            try:
                cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'flagged_listings'")
                if cursor.fetchone():
                    cursor.execute("SELECT listing_id FROM flagged_listings")
                    flagged_ids = {row['listing_id'] for row in cursor.fetchall()}
            except:
                pass

            # Compute latest import date and model stats for NEW/UNICORN badges.
            # UNICORN: a listing whose matched console has exactly one listing in
            # console_listings (all-time, unflagged). This is computed server-side
            # and is independent of the NEW/FIRST/STEAL/BUY client-side badges.
            latest_first_seen = None
            console_stats = {}
            try:
                cursor.execute("""
                    SELECT MAX(first_seen_at::date) as latest_date
                    FROM console_listings
                    WHERE first_seen_at IS NOT NULL
                """)
                result = cursor.fetchone()
                latest_first_seen = result['latest_date'] if result and result['latest_date'] else None
            except Exception:
                pass

            try:
                cursor.execute("""
                    SELECT
                        cl.matched_console_id,
                        ROUND(AVG(cl.price_eur)::numeric, 2) as avg_price,
                        MIN(cl.price_eur) as min_price,
                        MAX(cl.price_eur) as max_price,
                        COUNT(*) as listing_count
                    FROM console_listings cl
                    WHERE cl.matched_console_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = cl.listing_id)
                    GROUP BY cl.matched_console_id
                """)
                for row in cursor.fetchall():
                    console_stats[row['matched_console_id']] = dict(row)
            except Exception:
                pass

            cursor.close()

            # Enhance listings with flag status, derived console name, price stats,
            # NEW flag and UNICORN flag.
            enhanced_listings = []
            for listing in listings:
                listing_dict = dict(listing)
                listing_dict['is_flagged'] = listing_dict['listing_id'] in flagged_ids

                # Convert Decimal to float for JSON serialization
                if listing_dict.get('price_eur') is not None:
                    listing_dict['price_eur'] = float(listing_dict['price_eur'])

                # Extract console name from title if not matched
                if not listing_dict.get('console_name'):
                    title = listing_dict.get('title', '')
                    if 'playstation' in title.lower() or 'ps5' in title.lower() or 'ps4' in title.lower():
                        listing_dict['console_name'] = 'PlayStation'
                    elif 'xbox' in title.lower():
                        listing_dict['console_name'] = 'Xbox'
                    elif 'switch' in title.lower() or 'nintendo' in title.lower():
                        listing_dict['console_name'] = 'Nintendo Switch'
                    else:
                        listing_dict['console_name'] = 'Unknown Console'

                # NEW: from latest import date for console category
                if latest_first_seen and listing_dict.get('first_seen_at'):
                    fs = listing_dict['first_seen_at']
                    listing_date = fs.date() if hasattr(fs, 'date') else fs
                    listing_dict['is_new'] = listing_date == latest_first_seen
                else:
                    listing_dict['is_new'] = False

                # Price stats + UNICORN detection per matched console model
                matched_id = listing_dict.get('matched_console_id')
                if matched_id and matched_id in console_stats:
                    stats = console_stats[matched_id]
                    current_price = listing_dict.get('price_eur', 0)
                    avg_price = float(stats['avg_price']) if stats['avg_price'] else 0
                    min_price = float(stats['min_price']) if stats['min_price'] else 0
                    max_price = float(stats['max_price']) if stats['max_price'] else 0
                    count = int(stats['listing_count']) if stats['listing_count'] else 0

                    listing_dict['is_unicorn'] = count == 1
                    if count > 1:
                        listing_dict['price_stats'] = {
                            'avg': avg_price,
                            'min': min_price,
                            'max': max_price,
                            'below_avg': current_price < avg_price,
                            'percentile': round((current_price - min_price) / (max_price - min_price) * 100, 1)
                                          if max_price > min_price else 50,
                            'listing_count': count
                        }
                    else:
                        # Unicorn has no meaningful peer stats; keep price_stats None
                        listing_dict['price_stats'] = None
                else:
                    listing_dict['is_unicorn'] = False

                enhanced_listings.append(listing_dict)

            return jsonify(enhanced_listings)

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
        except:
            pass
        return jsonify([])


@app.route('/api/console-model-history/<int:console_id>')
@cache_control(max_age=30)
def get_console_model_history(console_id):
    """Get all historical prices for a specific console model."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Check if console tables exist
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'console_listings'
                )
            """)
            result = cursor.fetchone()
            table_exists = result.get('exists', False) if result else False

            if not table_exists:
                cursor.close()
                return jsonify([])

            cursor.execute("""
                SELECT
                    cl.listing_id,
                    cl.title,
                    cl.price_eur,
                    cl.seller_location,
                    COALESCE(cl.date_posted, cl.first_seen_at, cl.last_seen_at, cl.created_at) as date_posted,
                    cl.is_active,
                    cl.listing_url,
                    cl.image_url,
                    cl.local_image_path,
                    cl.console_confidence_score,
                    cr.name as console_name,
                    cv.model_name as variant_name,
                    ce.edition_name,
                    CASE WHEN fl.listing_id IS NOT NULL THEN TRUE ELSE FALSE END as is_flagged
                FROM console_listings cl
                LEFT JOIN console_reference cr ON cl.matched_console_id = cr.id
                LEFT JOIN console_variants cv ON cl.matched_variant_id = cv.id
                LEFT JOIN console_editions ce ON cl.matched_edition_id = ce.id
                LEFT JOIN flagged_listings fl ON cl.listing_id = fl.listing_id
                WHERE cl.matched_console_id = %s
                ORDER BY COALESCE(cl.date_posted, cl.first_seen_at, cl.last_seen_at, cl.created_at) DESC
            """, (console_id,))

            listings = cursor.fetchall()
            cursor.close()

            # Enhance with additional fields expected by frontend
            enhanced_listings = []
            for listing in listings:
                listing_dict = dict(listing)
                if not listing_dict.get('console_name'):
                    listing_dict['console_name'] = 'Unknown'
                enhanced_listings.append(listing_dict)

            return jsonify(enhanced_listings)

        except Exception as e:
            cursor.close()
            return jsonify({'error': str(e)}), 500


@app.route('/api/gpu-models-by-vendor')
@cache_control(max_age=30)
def get_gpu_models_by_vendor():
    """Get GPU models grouped by vendor for dropdown filters."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Query GPU reference table for models by vendor - sort by id desc (newer entries first)
            cursor.execute("""
                SELECT
                    vendor,
                    model,
                    vram_gb,
                    id
                FROM gpu_reference
                WHERE vendor IN ('NVIDIA', 'AMD', 'Intel')
                ORDER BY vendor, id DESC
            """)

            rows = cursor.fetchall()

            # Group by vendor (normalize DB casing to canonical keys)
            result = {
                'NVIDIA': {'models': [], 'vrams': {}},
                'AMD': {'models': [], 'vrams': {}},
                'Intel': {'models': [], 'vrams': {}}
            }
            vendor_map = {'NVIDIA': 'NVIDIA', 'AMD': 'AMD', 'INTEL': 'Intel'}

            for row in rows:
                vendor = vendor_map.get((row['vendor'] or '').upper(), row['vendor'])
                model = row['model']
                vram = row['vram_gb']

                if vendor in result:
                    if model not in result[vendor]['models']:
                        result[vendor]['models'].append(model)
                    if model not in result[vendor]['vrams']:
                        result[vendor]['vrams'][model] = []
                    if vram and vram not in result[vendor]['vrams'][model]:
                        result[vendor]['vrams'][model].append(vram)

            cursor.close()
            return jsonify(result)

    except Exception as e:
        import traceback
        print(f"ERROR in get_gpu_models_by_vendor: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-listing/<listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    """Delete a single listing from the database."""
    cursor = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # First delete any related records in flagged_listings
            cursor.execute("DELETE FROM flagged_listings WHERE listing_id = %s", (listing_id,))

            # Then delete the listing
            cursor.execute("DELETE FROM listings WHERE listing_id = %s", (listing_id,))

            if cursor.rowcount == 0:
                cursor.close()
                return jsonify({'success': False, 'error': 'Listing not found'}), 404

            conn.commit()
            cursor.close()

            return jsonify({'success': True, 'message': 'Listing deleted successfully'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        if cursor:
            cursor.close()
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bulk-delete-listings', methods=['POST'])
def bulk_delete_listings():
    """Delete multiple listings from the database."""
    cursor = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete related flags first, then listings
            cursor.execute(
                "DELETE FROM flagged_listings WHERE listing_id = ANY(%s::text[])",
                (listing_ids,)
            )
            cursor.execute(
                "DELETE FROM listings WHERE listing_id = ANY(%s::text[])",
                (listing_ids,)
            )

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()

            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Deleted {deleted_count} listing(s)'
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        if cursor:
            cursor.close()
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Project Board Routes
import json
import os

PROJECT_BOARD_FILE = os.path.join(os.path.dirname(__file__), 'data', 'project_board.json')

def load_project_board():
    """Load project board data from JSON file."""
    try:
        with open(PROJECT_BOARD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            log_board_loaded('file')
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_error('load_board', str(e))
        log_board_loaded('default_fallback')
        return {
            "columns": [
                {"id": "problems", "title": "Problems", "color": "#e74c3c", "tasks": []},
                {"id": "assignment", "title": "Assignment", "color": "#f39c12", "tasks": []},
                {"id": "talking", "title": "Talking", "color": "#9b59b6", "tasks": [
                    {
                        "id": "T001",
                        "title": "Setup OpenClaw Project Board",
                        "page": "General",
                        "category": "DevOps",
                        "priority": "High",
                        "column": "talking",
                        "created": "2026-06-17T23:30:00",
                        "updated": "2026-06-17T23:30:00"
                    },
                    {
                        "id": "T002",
                        "title": "RAM price calculation with outlier filtering",
                        "page": "RAM",
                        "category": "Backend",
                        "priority": "High",
                        "fix": "Use percentile-based filtering (10th-90th) with bounds checking",
                        "column": "talking",
                        "created": "2026-06-17T22:00:00",
                        "updated": "2026-06-17T22:30:00"
                    }
                ]},
                {"id": "progress", "title": "In Progress", "color": "#3498db", "tasks": []},
                {"id": "future", "title": "Future Box", "color": "#34495e", "tasks": []},
                {"id": "solved", "title": "Solved", "color": "#27ae60", "tasks": []}
            ],
            "next_id": 3,
            "categories": ["Backend", "Frontend", "UI/UX", "Database", "API", "Scraper", "DevOps", "Documentation"],
            "pages": ["CPU", "GPU", "RAM", "SSD", "Motherboards", "Monitors", "PSU", "Cases", "General"]
        }

def save_project_board(data):
    """Save project board data to JSON file."""
    os.makedirs(os.path.dirname(PROJECT_BOARD_FILE), exist_ok=True)
    with open(PROJECT_BOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    # Count total tasks
    task_count = sum(len(col['tasks']) for col in data.get('columns', []))
    log_board_saved(task_count)


def deduplicate_board_tasks(board):
    """Remove duplicate task IDs across columns, keeping the most relevant copy.

    Workflow priority (most active first): progress > assignment > problems >
    talking > solved > future. If a task ID appears in multiple columns, the copy
    in the higher-priority column wins; ties are broken by the most recent
    'updated' timestamp.
    """
    col_priority = {
        'progress': 5,
        'assignment': 4,
        'problems': 3,
        'talking': 2,
        'solved': 1,
        'future': 0
    }

    # Build map of task_id -> (priority, updated, column_index, task)
    seen = {}
    for idx, col in enumerate(board.get('columns', [])):
        col_id = col.get('id')
        priority = col_priority.get(col_id, -1)
        for task in col.get('tasks', []):
            tid = task.get('id')
            if not tid:
                continue
            updated = task.get('updated') or task.get('created') or ''
            current = seen.get(tid)
            if (current is None or
                priority > current[0] or
                (priority == current[0] and updated > current[1])):
                seen[tid] = (priority, updated, idx, task)

    # Remove duplicates from each column, keeping only the winner.
    winners = {tid: info[3] for tid, info in seen.items()}
    winner_col_idx = {tid: info[2] for tid, info in seen.items()}

    for idx, col in enumerate(board.get('columns', [])):
        filtered = []
        for task in col.get('tasks', []):
            tid = task.get('id')
            if not tid:
                continue
            if winner_col_idx.get(tid) == idx and winners.get(tid) is task:
                # Make sure the task's column metadata matches its actual column.
                task['column'] = col.get('id')
                filtered.append(task)
        col['tasks'] = filtered


def load_project_board():
    """Load project board data from JSON file."""
    try:
        with open(PROJECT_BOARD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            log_board_loaded('file')
            deduplicate_board_tasks(data)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_error('load_board', str(e))
        log_board_loaded('default_fallback')
        return {
            "columns": [
                {"id": "problems", "title": "Problems", "color": "#e74c3c", "tasks": []},
                {"id": "assignment", "title": "Assignment", "color": "#f39c12", "tasks": []},
                {"id": "talking", "title": "Talking", "color": "#9b59b6", "tasks": [
                    {
                        "id": "T001",
                        "title": "Setup OpenClaw Project Board",
                        "page": "General",
                        "category": "DevOps",
                        "priority": "High",
                        "column": "talking",
                        "created": "2026-06-17T23:30:00",
                        "updated": "2026-06-17T23:30:00"
                    },
                    {
                        "id": "T002",
                        "title": "RAM price calculation with outlier filtering",
                        "page": "RAM",
                        "category": "Backend",
                        "priority": "High",
                        "fix": "Use percentile-based filtering (10th-90th) with bounds checking",
                        "column": "talking",
                        "created": "2026-06-17T22:00:00",
                        "updated": "2026-06-17T22:30:00"
                    }
                ]},
                {"id": "progress", "title": "In Progress", "color": "#3498db", "tasks": []},
                {"id": "future", "title": "Future Box", "color": "#34495e", "tasks": []},
                {"id": "solved", "title": "Solved", "color": "#27ae60", "tasks": []}
            ],
            "next_id": 3,
            "categories": ["Backend", "Frontend", "UI/UX", "Database", "API", "Scraper", "DevOps", "Documentation"],
            "pages": ["CPU", "GPU", "RAM", "SSD", "Motherboards", "Monitors", "PSU", "Cases", "General"]
        }


@app.route('/project-board')
def project_board_page():
    """Render the project board page."""
    return render_template('project_board.html')


@app.route('/lens-icon-review')
def lens_icon_review_page():
    """Render the lens icon review/comparison page.

    Loads all 3 icon variants (simple, detailed, realistic) for every known
    lens key, lets the user mark each as good/bad/rework/skip, and stores
    the marks in the `lens_icon_reviews` table. A summary block lists the
    pending 'rework' items so the assistant can pick them up later.
    """
    return render_template('lens_icon_review.html')


@app.route('/api/lens-icon-reviews', methods=['GET'])
def get_lens_icon_reviews():
    """Return all stored reviews keyed by (lens_key, icon_source)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lens_key, icon_source, rating, comment, reviewed_at
                FROM lens_icon_reviews
            """)
            rows = cursor.fetchall()
            cursor.close()
        return jsonify({
            'reviews': [
                {
                    'lens_key': r[0],
                    'icon_source': r[1],
                    'rating': r[2],
                    'comment': r[3],
                    'reviewed_at': r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({'reviews': [], 'error': str(e)}), 500


@app.route('/api/lens-icon-reviews', methods=['POST'])
def post_lens_icon_review():
    """Upsert a single review. Body: {lens_key, icon_source, rating, comment}."""
    data = request.get_json(silent=True) or {}
    lens_key = data.get('lens_key')
    icon_source = data.get('icon_source')
    rating = data.get('rating')
    comment = (data.get('comment') or '').strip()

    if not lens_key or icon_source not in ('simple', 'detailed', 'realistic') or \
       rating not in ('good', 'bad', 'rework', 'skip'):
        return jsonify({'success': False, 'error': 'invalid input'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lens_icon_reviews (lens_key, icon_source, rating, comment, reviewed_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (lens_key, icon_source) DO UPDATE SET
                    rating = EXCLUDED.rating,
                    comment = EXCLUDED.comment,
                    reviewed_at = CURRENT_TIMESTAMP
            """, (lens_key, icon_source, rating, comment))
            conn.commit()
            cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lens-icon-reviews', methods=['DELETE'])
def delete_lens_icon_review():
    """Remove a single review. Body: {lens_key, icon_source}."""
    data = request.get_json(silent=True) or {}
    lens_key = data.get('lens_key')
    icon_source = data.get('icon_source')

    if not lens_key or icon_source not in ('simple', 'detailed', 'realistic'):
        return jsonify({'success': False, 'error': 'invalid input'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lens_icon_reviews WHERE lens_key = %s AND icon_source = %s", (lens_key, icon_source))
            conn.commit()
            cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/project-board')
def get_project_board():
    """Get project board data.

    NOTE: Do NOT add @cache_control here. The project board is a JSON file
    that mutates on every user action (solve/reopen/move/edit), and the
    `cache_control` decorator's ETag is computed from the unrelated
    `listings` table — which means after a successful move the next
    loadBoard() either gets a 30s-stale cached response or a 304 with
    an empty body, leaving the UI showing the ticket "stuck" in its
    previous column even though the move succeeded server-side.
    """
    response = jsonify(load_project_board())
    # Prevent any browser or intermediate cache from holding a stale copy
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/project-board/task', methods=['POST'])
def add_project_task():
    """Add a new task to the project board."""
    data = request.get_json()
    board = load_project_board()

    # Ensure next_id exists - if not, find the highest task ID from all columns
    if 'next_id' not in board:
        max_id = 0
        for col in board.get('columns', []):
            for task in col.get('tasks', []):
                try:
                    # Parse task ID like "T001" to get number
                    task_num = int(task.get('id', 'T0')[1:])
                    max_id = max(max_id, task_num)
                except (ValueError, IndexError):
                    continue
        board['next_id'] = max_id + 1

    task = {
        "id": f"T{board['next_id']:03d}",
        "title": data.get('title'),
        "page": data.get('page', ''),
        "category": data.get('category', ''),
        "priority": data.get('priority', 'Medium'),
        "fix": data.get('fix', ''),
        "code_snippet": data.get('code_snippet', ''),
        "language": data.get('language', ''),
        "future_folder_id": data.get('future_folder_id'),
        "column": data.get('column', 'problems'),
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }

    # Don't store empty optional fields
    if not task['code_snippet']:
        del task['code_snippet']
    if not task['language']:
        del task['language']
    if not task['future_folder_id']:
        del task['future_folder_id']

    # Handle linked tasks (new format: array) or single link (backward compat)
    linked_tasks = data.get('linked_tasks')
    if linked_tasks and len(linked_tasks) > 0:
        task['linked_tasks'] = linked_tasks
        # Also set single link for backward compat
        task['linked_task_id'] = linked_tasks[0]['task_id']
        task['relationship_type'] = linked_tasks[0]['relationship_type']
    else:
        # Backward compatibility - old format
        task['linked_task_id'] = data.get('linked_task_id')
        task['relationship_type'] = data.get('relationship_type')

    for col in board['columns']:
        if col['id'] == task['column']:
            col['tasks'].append(task)
            break

    board['next_id'] += 1
    save_project_board(board)

    # Log task creation
    log_task_created(task)

    return jsonify({'success': True, 'task': task})

@app.route('/api/project-board/reopen', methods=['POST'])
def reopen_project_task():
    """Re-open a task with update text."""
    data = request.get_json()
    board = load_project_board()

    task_id = data.get('task_id')
    to_column = data.get('to_column', 'assignment')
    update_text = data.get('update', '')

    task = None
    for col in board['columns']:
        for t in col['tasks']:
            if t['id'] == task_id:
                task = t
                col['tasks'].remove(t)
                break
        if task:
            break

    if task:
        # Store original column for rollback if needed
        original_column = task.get('column', 'solved')

        task['column'] = to_column
        task['updated'] = datetime.now().isoformat()

        # Store re-open history
        if 'reopen_history' not in task:
            task['reopen_history'] = []

        task['reopen_history'].append({
            'reopened_at': datetime.now().isoformat(),
            'update': update_text,
            'previous_completed_at': task.get('completed_at')
        })

        # Set linked task and relationship if provided
        linked_tasks = data.get('linked_tasks')
        if linked_tasks and len(linked_tasks) > 0:
            task['linked_tasks'] = linked_tasks
            # Also set single link for backward compat
            task['linked_task_id'] = linked_tasks[0]['task_id']
            task['relationship_type'] = linked_tasks[0]['relationship_type']
        else:
            # Backward compatibility - old format
            linked_task_id = data.get('linked_task_id')
            if linked_task_id:
                task['linked_task_id'] = linked_task_id
            relationship_type = data.get('relationship_type')
            if relationship_type:
                task['relationship_type'] = relationship_type

        # Clear completed_at since it's now re-opened
        if 'completed_at' in task:
            del task['completed_at']

        # Store the code snippet if provided on reopen
        code_snippet = data.get('code_snippet', '').strip()
        if code_snippet:
            task['code_snippet'] = code_snippet
        language = data.get('language', '').strip()
        if language:
            task['language'] = language

        # Add to target column
        target_found = False
        for col in board['columns']:
            if col['id'] == to_column:
                col['tasks'].append(task)
                target_found = True
                break

        # CRITICAL FIX: If target column not found, restore to original column
        if not target_found:
            log_error('REOPEN', f"Target column '{to_column}' not found, restoring task {task_id} to '{original_column}'")
            for col in board['columns']:
                if col['id'] == original_column:
                    task['column'] = original_column
                    col['tasks'].append(task)
                    break
            deduplicate_board_tasks(board)
            save_project_board(board)
            return jsonify({'success': False, 'error': f'Target column "{to_column}" not found'}), 400

        deduplicate_board_tasks(board)
        save_project_board(board)

        # Log re-open
        log_task_reopened(task_id, update_text)

        return jsonify({'success': True, 'task': task})

    return jsonify({'success': False, 'error': 'Task not found'}), 404

@app.route('/api/project-board/move', methods=['POST'])
def move_project_task():
    """Move a task between columns."""
    data = request.get_json()
    board = load_project_board()

    task_id = data.get('task_id')
    to_column = data.get('to_column')

    task = None
    for col in board['columns']:
        for t in col['tasks']:
            if t['id'] == task_id:
                task = t
                col['tasks'].remove(t)
                break
        if task:
            break

    if task:
        from_column = task.get('column', 'unknown')
        task['column'] = to_column
        task['updated'] = datetime.now().isoformat()

        # Capture the fix text associated with this move (e.g. when solving a reopened task)
        move_fix = data.get('fix')
        if move_fix is not None:
            task['fix'] = move_fix
            # Store the fix in the latest reopen_history entry so we can analyze per-reopen solutions
            history = task.get('reopen_history', [])
            if history:
                history[-1]['fix'] = move_fix

        # Set completed_at when moving to solved, preserve if already set
        if to_column == 'solved':
            if 'completed_at' not in task:
                task['completed_at'] = datetime.now().isoformat()
                log_task_marked_solved(task_id)
        else:
            # Remove completed_at when moving out of solved
            if 'completed_at' in task:
                del task['completed_at']

        for col in board['columns']:
            if col['id'] == to_column:
                col['tasks'].append(task)
                break

        deduplicate_board_tasks(board)
        save_project_board(board)

        # Log the move
        log_task_moved(task_id, from_column, to_column)

        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Task not found'}), 404

@app.route('/api/project-board/task/<task_id>', methods=['PUT'])
def update_project_task(task_id):
    """Update an existing task's fields (including relationship)."""
    data = request.get_json()
    board = load_project_board()

    task = None
    for col in board['columns']:
        for t in col['tasks']:
            if t['id'] == task_id:
                task = t
                break
        if task:
            break

    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    # Update allowed fields
    updatable_fields = ['title', 'page', 'category', 'priority', 'fix', 'code_snippet', 'language', 'linked_task_id', 'relationship_type', 'future_folder_id', 'folder_id']
    for field in updatable_fields:
        if field in data:
            task[field] = data[field]

    # Remove empty optional snippet/language fields
    if 'code_snippet' in task and not task['code_snippet']:
        del task['code_snippet']
    if 'language' in task and not task['language']:
        del task['language']

    # Remove future_folder_id if explicitly set to null/empty
    if 'future_folder_id' in data and not data['future_folder_id']:
        task.pop('future_folder_id', None)
    if 'folder_id' in data and not data['folder_id']:
        task.pop('folder_id', None)

    # Handle linked_tasks array
    if 'linked_tasks' in data:
        task['linked_tasks'] = data['linked_tasks']
        if data['linked_tasks'] and len(data['linked_tasks']) > 0:
            task['linked_task_id'] = data['linked_tasks'][0]['task_id']
            task['relationship_type'] = data['linked_tasks'][0]['relationship_type']

    task['updated'] = datetime.now().isoformat()
    save_project_board(board)

    return jsonify({'success': True, 'task': task})


@app.route('/api/project-board/task/<task_id>/reopen-history/<int:idx>', methods=['PUT'])
def update_project_task_reopen_history(task_id, idx):
    """Edit the text of a specific reopen-history entry."""
    data = request.get_json()
    board = load_project_board()

    task = None
    for col in board['columns']:
        for t in col['tasks']:
            if t['id'] == task_id:
                task = t
                break
        if task:
            break

    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    history = task.get('reopen_history', [])
    if not history or idx < 0 or idx >= len(history):
        return jsonify({'success': False, 'error': 'Reopen history entry not found'}), 404

    new_update = data.get('update', '').strip()
    if not new_update:
        return jsonify({'success': False, 'error': 'Update text cannot be empty'}), 400

    history[idx]['update'] = new_update
    task['updated'] = datetime.now().isoformat()
    save_project_board(board)

    return jsonify({'success': True, 'task': task})


@app.route('/api/project-board/task/<task_id>', methods=['DELETE'])
def delete_project_task(task_id):
    """Delete a task from the project board."""
    board = load_project_board()

    for col in board['columns']:
        for t in col['tasks']:
            if t['id'] == task_id:
                task_title = t.get('title', 'Unknown')
                col['tasks'].remove(t)
                save_project_board(board)

                # Log deletion
                log_task_deleted(task_id, task_title)

                return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Task not found'}), 404


# Future Column Folders API
@app.route('/api/project-board/folder', methods=['POST'])
def create_folder():
    """Create a new folder in the Future column."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    data = request.get_json()
    folder_id = f'F-{datetime.now().strftime("%Y%m%d%H%M%S")}-{os.urandom(4).hex()[:8]}'

    new_folder = {
        'id': folder_id,
        'name': data.get('name', 'New Folder'),
        'description': data.get('description', ''),
        'relationship_status': data.get('relationship_status', 'planned'),
        'folder_class': data.get('folder_class', 'Feature'),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'expanded': True
    }

    for col in board['columns']:
        if col['id'] == 'future':
            if 'folders' not in col:
                col['folders'] = []
            col['folders'].append(new_folder)
            break

    with open(BOARD_FILE, 'w') as f:
        json.dump(board, f, indent=2)

    return jsonify({'folder': new_folder}), 201


@app.route('/api/project-board/folder/<folder_id>', methods=['PUT'])
def update_folder(folder_id):
    """Update a folder."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    data = request.get_json()

    for col in board['columns']:
        if col['id'] == 'future':
            for folder in col.get('folders', []):
                if folder['id'] == folder_id:
                    folder['name'] = data.get('name', folder['name'])
                    folder['description'] = data.get('description', folder.get('description', ''))
                    folder['relationship_status'] = data.get('relationship_status', folder.get('relationship_status', 'planned'))
                    folder['folder_class'] = data.get('folder_class', folder.get('folder_class', 'Feature'))
                    if 'expanded' in data:
                        folder['expanded'] = bool(data['expanded'])
                    folder['updated_at'] = datetime.now().isoformat()

                    with open(BOARD_FILE, 'w') as f:
                        json.dump(board, f, indent=2)

                    return jsonify({'folder': folder}), 200

    return jsonify({'error': 'Folder not found'}), 404


@app.route('/api/project-board/folder/<folder_id>/toggle', methods=['POST'])
def toggle_folder(folder_id):
    """Toggle a Future folder's expanded/collapsed state."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    for col in board['columns']:
        if col['id'] == 'future':
            for folder in col.get('folders', []):
                if folder['id'] == folder_id:
                    folder['expanded'] = not folder.get('expanded', True)
                    folder['updated_at'] = datetime.now().isoformat()

                    with open(BOARD_FILE, 'w') as f:
                        json.dump(board, f, indent=2)

                    return jsonify({'success': True, 'folder': folder}), 200

    return jsonify({'error': 'Folder not found'}), 404


@app.route('/api/project-board/folder/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder and move tasks to unfiled."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    for col in board['columns']:
        if col['id'] == 'future':
            # Move tasks to unfiled
            for task in col.get('tasks', []):
                if task.get('folder_id') == folder_id:
                    task['folder_id'] = None

            # Remove folder
            col['folders'] = [f for f in col.get('folders', []) if f['id'] != folder_id]

            with open(BOARD_FILE, 'w') as f:
                json.dump(board, f, indent=2)

            return jsonify({'success': True}), 200

    return jsonify({'error': 'Folder not found'}), 404


@app.route('/api/project-board/task-folder', methods=['POST'])
def move_task_to_folder():
    """Move a task to a folder (moves task to future column)."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    data = request.get_json()
    task_id = data.get('task_id')
    folder_id = data.get('folder_id')
    mark_as_future = data.get('mark_as_future', True)  # Default to True for backward compatibility

    task = None
    task_column = None

    # Search ALL columns for the task
    for col in board['columns']:
        for t in col.get('tasks', []):
            if t['id'] == task_id:
                task = t
                task_column = col['id']
                break
        if task:
            break

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    # Store folder_id in task regardless
    task['folder_id'] = folder_id
    task['future_folder_id'] = folder_id  # Also store for "similar_to" relationship tracking
    task['updated_at'] = datetime.now().isoformat()
    task['updated'] = datetime.now().isoformat()

    # If mark_as_future is True, move task to future column
    # If False, just update the folder reference without moving (used for "similar_to" tasks)
    if mark_as_future:
        # If task is not already in 'future' column, move it there
        if task_column != 'future':
            # Remove from current column
            for col in board['columns']:
                if col['id'] == task_column:
                    col['tasks'] = [t for t in col['tasks'] if t['id'] != task_id]
                    break

            # Add to future column
            for col in board['columns']:
                if col['id'] == 'future':
                    task['column'] = 'future'
                    col['tasks'].append(task)
                    break

    with open(BOARD_FILE, 'w') as f:
        json.dump(board, f, indent=2)

    return jsonify({'success': True}), 200


@app.route('/api/project-board/logs')
@cache_control(max_age=30)
def get_project_board_logs():
    """Get recent project board activity logs."""
    try:
        from board_logger import get_recent_logs
        logs = get_recent_logs(lines=100)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Task Notes API
TASK_NOTES_FILE = r'G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_notes.json'

def load_task_notes():
    """Load task notes from JSON file."""
    try:
        with open(TASK_NOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_task_notes(notes):
    """Save task notes to JSON file."""
    os.makedirs(os.path.dirname(TASK_NOTES_FILE), exist_ok=True)
    with open(TASK_NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, indent=2)

def append_note_to_markdown(task_id, text):
    """Append note to the markdown file for persistence."""
    md_file = r'G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_notes.md'
    os.makedirs(os.path.dirname(md_file), exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(md_file, 'a', encoding='utf-8') as f:
        f.write(f"\n## {task_id} - {timestamp}\n\n")
        f.write(f"{text}\n")
        f.write("\n---\n")

@app.route('/api/project-notes', methods=['GET'])
def get_task_notes():
    """Get notes for a specific task."""
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'error': 'task_id required'}), 400

    notes = load_task_notes()
    task_notes = notes.get(task_id, [])
    return jsonify({'notes': task_notes})

@app.route('/api/project-notes', methods=['POST'])
def add_task_note():
    """Add a note to a specific task."""
    data = request.get_json()
    task_id = data.get('task_id')
    text = data.get('text', '').strip()

    if not task_id or not text:
        return jsonify({'error': 'task_id and text required'}), 400

    # Block auto-generated/accidental notes
    blocked_phrases = [
        'everything has disappered from the dropdown list',
        'everything has disappeared from the dropdown list'
    ]
    if any(phrase in text.lower() for phrase in blocked_phrases):
        return jsonify({'error': 'Note contains auto-generated text. Please type a meaningful note.'}), 400

    notes = load_task_notes()
    if task_id not in notes:
        notes[task_id] = []

    note = {
        'text': text,
        'timestamp': datetime.now().isoformat()
    }
    notes[task_id].append(note)
    save_task_notes(notes)

    # Also append to markdown file
    append_note_to_markdown(task_id, text)

    return jsonify({'success': True, 'note': note})


@app.route('/api/project-board/task-special', methods=['POST'])
def toggle_task_special():
    """Toggle special status on a task."""
    BOARD_FILE = r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\data\\project_board.json'

    with open(BOARD_FILE, 'r') as f:
        board = json.load(f)

    data = request.get_json()
    task_id = data.get('task_id')
    special = data.get('special', False)

    for col in board['columns']:
        for task in col.get('tasks', []):
            if task['id'] == task_id:
                task['special'] = special
                task['updated'] = datetime.now().isoformat()

                with open(BOARD_FILE, 'w') as f:
                    json.dump(board, f, indent=2)

                return jsonify({'success': True, 'task': task}), 200

    return jsonify({'error': 'Task not found'}), 404





@app.route('/api/set-language', methods=['POST'])
def api_set_language():
    data = request.get_json(silent=True) or {}
    lang = str(data.get('lang', 'en')).strip().lower()
    if lang not in ('en', 'lv'):
        lang = 'en'
    flask_session['lang'] = lang
    resp = make_response(jsonify({'lang': lang}))
    resp.set_cookie('ss_lang', lang, max_age=60*60*24*365, samesite='Lax')
    return resp

# Auth setup: run inside app context to avoid circular import issues
with app.app_context():
    from auth import get_current_user, get_user_allowed_pages, require_login as _require_login, require_role as _require_role

    @app.before_request
    def load_current_user():
        from auth import get_current_user, get_user_allowed_pages
        # Language preference from query param, cookie, or session
        lang = request.args.get('lang') or request.cookies.get('ss_lang') or flask_session.get('lang') or 'en'
        if lang not in ('en', 'lv'):
            lang = 'en'
        flask_session['lang'] = lang
        g.lang = lang
        user = get_current_user()
        g.current_user = user
        if user:
            g.hide_unmatched_default = _get_toggle_role_default(user.get('role', 'user'), 'hideUnmatchedListings')
        else:
            # Anonymous user → use the canonical default for the 'user' role
            g.hide_unmatched_default = _get_toggle_role_default('user', 'hideUnmatchedListings')
        # Per-request override: ?hide_unmatched=1 or ?hide_unmatched=0
        hu = request.args.get('hide_unmatched')
        if hu is not None:
            g.hide_unmatched_listings = hu in ('1', 'true', 'yes')
        else:
            g.hide_unmatched_listings = bool(g.hide_unmatched_default)
        if user:
            g.allowed_pages = get_user_allowed_pages(user['id'], user['role'])
        else:
            g.allowed_pages = set(get_role_defaults('user'))

    def require_login(f):
        @_require_login
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper

    def require_role(min_role):
        return _require_role(min_role)

    def page_access(page):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                if page not in g.get('allowed_pages', set()):
                    return "Forbidden", 403
                return f(*args, **kwargs)
            return wrapper
        return decorator

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        from auth import authenticate_user, create_session
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = authenticate_user(username, password)
        if not user:
            return render_template('login.html', error='Invalid username or password'), 401
        token = create_session(user['id'])
        resp = make_response(redirect('/'))
        resp.set_cookie('session_token', token, httponly=True, samesite='Lax', max_age=60*60*24*30)
        return resp

    @app.route('/logout')
    def logout():
        from auth import delete_session
        token = request.cookies.get('session_token')
        if token:
            delete_session(token)
        resp = make_response(redirect('/login'))
        resp.set_cookie('session_token', '', expires=0)
        return resp

    @app.route('/api/auth/me')
    def api_me():
        """Return the current user, or {authenticated: false, user: null}.

        Intentionally returns 200 (not 401) when no user is logged in, so:
          1. The browser does not log the response to the console as an error
             (browsers log all 4xx to console by design).
          2. There is no 30-second HTTP cache holding the unauthenticated
             state — after login, the next /api/auth/me returns the
             authenticated state immediately.
        """
        user = g.get('current_user')
        if not user:
            response = jsonify({"authenticated": False, "user": None})
        else:
            response = jsonify({
                "authenticated": True,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "role": user['role'],
                    "subscription_status": user['subscription_status'],
                    "subscription_tier": user['subscription_tier'],
                    "subscription_expires_at": user['subscription_expires_at'],
                    "allowed_pages": sorted(g.get('allowed_pages', set()))
                }
            })
        # Never cache — auth state changes on every login/logout.
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/profile')
    @require_login
    def profile():
        user = g.get('current_user')
        return render_template('profile.html', user=user, allowed_pages=sorted(g.get('allowed_pages', set())))

    @app.route('/admin')
    @require_login
    @require_role('admin')
    def admin_panel():
        from auth import get_all_users, PAGES, ROLES, get_role_defaults
        users = get_all_users()
        role_defaults = {role: sorted(get_role_defaults(role)) for role in ROLES}
        return render_template('admin.html', users=users, role_defaults=role_defaults, pages=PAGES, roles=ROLES)

    @app.route('/api/admin/users', methods=['GET', 'POST'])
    @require_login
    @require_role('admin')
    def api_admin_users():
        from auth import get_all_users, create_user, update_user, delete_user
        if request.method == 'GET':
            return jsonify(get_all_users())
        data = request.get_json() or {}
        action = data.get('action')
        if action == 'create':
            user_id, err = create_user(
                data['username'], data['password'], data.get('email'),
                data.get('role', 'user'), data.get('subscription_status', 'inactive')
            )
            if err:
                return jsonify({"error": err}), 400
            return jsonify({"id": user_id}), 201
        if action == 'update':
            fields = {k: data[k] for k in ['email', 'role', 'subscription_status', 'subscription_tier', 'is_active'] if k in data}
            if 'password' in data and data['password']:
                fields['password'] = data['password']
            ok, err = update_user(data['id'], **fields)
            if not ok:
                return jsonify({"error": err}), 400
            return jsonify({"ok": True})
        if action == 'delete':
            if delete_user(data['id']):
                return jsonify({"ok": True})
            return jsonify({"error": "User not found"}), 404
        return jsonify({"error": "Unknown action"}), 400

    @app.route('/api/admin/role-access', methods=['POST'])
    @require_login
    @require_role('admin')
    def api_admin_role_access():
        from auth import set_role_defaults
        data = request.get_json() or {}
        roles_data = data.get('roles')
        if roles_data and isinstance(roles_data, dict):
            ok = True
            for role, allowed_pages in roles_data.items():
                if not set_role_defaults(role, allowed_pages or []):
                    ok = False
            if not ok:
                return jsonify({"error": "Failed to update role access"}), 500
            return jsonify({"ok": True})
        # Legacy single-role payload
        role = data.get('role')
        allowed_pages = data.get('allowed_pages', [])
        if not role:
            return jsonify({"error": "Missing role"}), 400
        ok = set_role_defaults(role, allowed_pages)
        if not ok:
            return jsonify({"error": "Failed to update role access"}), 500
        return jsonify({"ok": True})

    @app.route('/api/admin/user-access', methods=['POST'])
    @require_login
    @require_role('admin')
    def api_admin_user_access():
        from auth import set_user_page_access
        data = request.get_json() or {}
        ok = set_user_page_access(data['user_id'], data.get('allowed_pages', []), data.get('denied_pages', []))
        if not ok:
            return jsonify({"error": "Failed to update user access"}), 500
        return jsonify({"ok": True})

    # ----------------------------------------------------------------
    # Admin page toggles — per-role defaults + per-user overrides
    # ----------------------------------------------------------------
    #
    # The toggle list is canonical: it lives here in TOGGLE_DEFINITIONS
    # and is shared with the admin.html UI. Each toggle can be enabled
    # or disabled per role. Per-user localStorage overrides still work
    # and take precedence over the role default (so power users can
    # still flip a toggle for their own browser without admin help).
    #
    # Endpoints:
    #   GET  /api/admin/toggle-defaults   -> {"toggles": [{key, label, role_default, ...}, ...]}
    #                                       any logged-in user can read their role's defaults
    #   GET  /api/admin/toggle-matrix     -> {role: {toggle_key: bool, ...}, ...}  (admin only)
    #   POST /api/admin/toggle-defaults   -> {toggles: {role: {toggle_key: bool, ...}, ...}}  (admin only)
    TOGGLE_DEFINITIONS = [
        # (key, label, default_for_user, applies_to_pages)
        ("showListingId",                "Show listing IDs",                    True,  "all"),
        ("showGPUId",                    "Show GPU matched ID",                  True,  "gpu"),
        ("showSourceDots",               "Show source dots",                     True,  "all"),
        ("showSummaryFields",            "Show summary fields",                  True,  "all"),
        ("showDeleteButtons",            "Show delete buttons",                  False, "all"),
        ("showGeForceInGPUName",         "Show \"GeForce\" in NVIDIA names",     True,  "gpu"),
        ("enableRAMColumnCustomization", "Enable RAM column customization",      True,  "ram"),
        ("showRAMConfidenceBar",         "Show RAM confidence bar under name",   True,  "ram"),
        ("showSsdIds",                   "Show SSD ID + listing ID in popup",    False, "ssd"),
        ("hideUnmatchedListings",        "Hide unmatched listings on all pages", False, "all"),
    ]
    TOGGLE_KEYS = {t[0] for t in TOGGLE_DEFINITIONS}
    TOGGLE_META = {t[0]: {"label": t[1], "default": t[2], "applies_to": t[3]} for t in TOGGLE_DEFINITIONS}

    # Map a category to the column that signals "this listing has been
    # matched to a reference model". Used by _unmatched_filter_sql().
    _CATEGORY_MATCH_COLUMN = {
        'gpu':         'matched_gpu_id',
        'cpu':         'matched_cpu_id',
        'ssd':         'matched_ssd_id',
        'ram':         'matched_ram_id',
        'psu':         'matched_psu_id',
        'case':        'matched_case_id',
        'motherboard': 'motherboard_model_id',
        'monitor':     'monitor_model_id',
        'camera':      'matched_camera_id',
        'lens':        'matched_lens_id',
        'console':     'matched_console_id',
    }

    def _unmatched_filter_sql(category, table_alias='l'):
        """Return an SQL fragment to hide listings that haven't been
        matched to a reference model. Returns '' if the user's toggle
        is off, or if the category has no match column.

        Usage in a listing endpoint:
            query += _unmatched_filter_sql('case')
        """
        if not getattr(g, 'hide_unmatched_listings', False):
            return ''
        col = _CATEGORY_MATCH_COLUMN.get(category)
        if not col:
            return ''
        if category == 'computer':
            # computer_listings has multiple match columns. Hide a row
            # only if ALL match columns are NULL.
            return (
                f' AND ({table_alias}.matched_cpu_id IS NOT NULL '
                f'OR {table_alias}.matched_gpu_id IS NOT NULL '
                f'OR {table_alias}.matched_ram_id IS NOT NULL '
                f'OR {table_alias}.matched_ssd_id IS NOT NULL '
                f'OR {table_alias}.matched_psu_id IS NOT NULL '
                f'OR {table_alias}.matched_case_id IS NOT NULL '
                f'OR {table_alias}.motherboard_model_id IS NOT NULL) '
            )
        return f' AND {table_alias}.{col} IS NOT NULL '

    def _get_toggle_role_default(role, toggle_key):
        """Return the role's default for a toggle (True/False) or the
        global fallback if no row exists yet."""
        fallback = TOGGLE_META.get(toggle_key, {}).get("default", True)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT enabled FROM role_toggle_defaults WHERE role = %s AND toggle_key = %s",
                    (role, toggle_key)
                )
                row = cursor.fetchone()
                cursor.close()
                if row is None:
                    return fallback
                return bool(row[0])
        except Exception as e:
            app.logger.warning(f"_get_toggle_role_default failed for {role}/{toggle_key}: {e}")
            return fallback

    def _set_toggle_role_default(role, toggle_key, enabled):
        """Upsert a single (role, toggle_key) -> enabled row."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO role_toggle_defaults (role, toggle_key, enabled, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (role, toggle_key)
                DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = NOW()
                """,
                (role, toggle_key, bool(enabled))
            )
            conn.commit()
            cursor.close()

    @app.route('/api/admin/toggle-defaults', methods=['GET'])
    @require_login
    def api_admin_toggle_defaults_get():
        """Return the list of toggles and the current user's role default
        for each one. The page-level JS then layers on the user's
        localStorage override (if any)."""
        user = g.get('current_user') or {}
        role = user.get('role', 'user')
        toggles = []
        for key, label, default, applies_to in TOGGLE_DEFINITIONS:
            toggles.append({
                "key": key,
                "label": label,
                "applies_to": applies_to,
                "role_default": _get_toggle_role_default(role, key),
            })
        return jsonify({"role": role, "toggles": toggles})

    @app.route('/api/admin/toggle-defaults', methods=['POST'])
    @require_login
    @require_role('admin')
    def api_admin_toggle_defaults_set():
        """Save the role x toggle matrix. Body:
            {"toggles": {"user": {"showDeleteButtons": true, ...}, "admin": {...}, ...}}
        Unknown toggle keys are silently ignored.
        """
        from auth import ROLES
        data = request.get_json() or {}
        toggles = data.get("toggles") or {}
        if not isinstance(toggles, dict):
            return jsonify({"error": "toggles must be an object"}), 400
        try:
            for role, role_toggles in toggles.items():
                if role not in ROLES:
                    continue
                if not isinstance(role_toggles, dict):
                    continue
                for key, enabled in role_toggles.items():
                    if key not in TOGGLE_KEYS:
                        continue
                    _set_toggle_role_default(role, key, bool(enabled))
            return jsonify({"ok": True})
        except Exception as e:
            app.logger.error(f"Failed to save toggle defaults: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/admin/toggle-matrix', methods=['GET'])
    @require_login
    @require_role('admin')
    def api_admin_toggle_matrix():
        """Return the full role x toggle matrix (admin only) for the
        admin panel."""
        from auth import ROLES
        matrix = {role: {} for role in ROLES}
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, toggle_key, enabled FROM role_toggle_defaults")
                for role, key, enabled in cursor.fetchall():
                    if role in matrix and key in TOGGLE_KEYS:
                        matrix[role][key] = bool(enabled)
                cursor.close()
        except Exception as e:
            app.logger.error(f"Failed to load toggle matrix: {e}")
            return jsonify({"error": str(e)}), 500
        # Fill in any missing cells with the canonical default
        for role in matrix:
            for key in TOGGLE_KEYS:
                if key not in matrix[role]:
                    matrix[role][key] = TOGGLE_META[key]["default"]
        return jsonify({"matrix": matrix, "toggles": [{"key": k, "label": v["label"], "applies_to": v["applies_to"]} for k, v in TOGGLE_META.items()]})

    @app.route('/api/subscription/plans')
    @cache_control(max_age=30)
    def api_subscription_plans():
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute("SELECT * FROM subscription_plans WHERE is_active = true ORDER BY price_eur NULLS LAST")
                return jsonify(cursor.fetchall())
            finally:
                cursor.close()

    @app.route('/api/profile', methods=['POST'])
    @require_login
    def api_update_profile():
        from auth import update_user
        user = g.get('current_user')
        data = request.get_json() or {}
        fields = {}
        if 'email' in data:
            fields['email'] = data['email']
        if 'password' in data and data['password']:
            fields['password'] = data['password']
        ok, err = update_user(user['id'], **fields)
        if not ok:
            return jsonify({"error": err}), 400
        return jsonify({"ok": True})


@app.route('/api/laptops/cities')
@cache_control(max_age=30)
def laptop_cities():
    """Distinct seller_location values from active laptop listings, for the
    city filter dropdown. Limited to cities with >= 2 active listings so the
    dropdown stays sensible."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT seller_location AS city, COUNT(*) AS n
                FROM laptop_listings
                WHERE is_active = true
                  AND seller_location IS NOT NULL
                  AND TRIM(seller_location) <> ''
                GROUP BY seller_location
                HAVING COUNT(*) >= 1
                ORDER BY n DESC, city ASC
                LIMIT 60
            """)
            rows = cursor.fetchall()
            return jsonify({'cities': [r['city'] for r in rows]})
        except Exception as e:
            return jsonify({'cities': [], 'error': str(e)}), 500
        finally:
            cursor.close()


@app.route('/api/laptops/cpu-options')
@cache_control(max_age=30)
def laptop_cpu_options():
    """Distinct canonical CPU models (from laptop_reference_cpu) for the
    CPU filter popup. Returns {ref_id, brand, model, listing_count} so the
    frontend can group by vendor, show just the model in the list, and send
    the ref_id as the filter value (more accurate than ILIKE on cpu_raw).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT lrc.id, lrc.brand, lrc.model, COUNT(ll.id) AS listing_count
                FROM laptop_reference_cpu lrc
                JOIN laptop_listings ll ON ll.cpu_reference_id = lrc.id
                WHERE ll.is_active = true
                  AND NOT EXISTS (
                      SELECT 1 FROM flagged_listings fl
                      WHERE fl.listing_id = ll.listing_id AND fl.category = 'laptop'
                  )
                GROUP BY lrc.id, lrc.brand, lrc.model
                ORDER BY lrc.brand, lrc.model
            """)
            return jsonify({'cpus': [dict(r) for r in cursor.fetchall()]})
        except Exception as e:
            return jsonify({'cpus': [], 'error': str(e)}), 500
        finally:
            cursor.close()


@app.route('/api/laptop-reference/stats')
@cache_control(max_age=30)
def laptop_reference_stats():
    """Lightweight counts for the Laptops page hero stat tiles.

    Public (no auth) — same exposure level as the listing endpoints. The numbers
    are aggregate counts and reveal no per-listing data.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT COUNT(*) AS n FROM laptop_reference")
            models = cursor.fetchone()['n']
            cursor.execute("SELECT COUNT(*) AS n FROM laptop_reference WHERE is_valid = true")
            valid = cursor.fetchone()['n']
            cursor.execute(
                "SELECT COUNT(*) AS n FROM laptop_reference "
                "WHERE resolution IS NOT NULL AND resolution <> ''"
            )
            with_resolution = cursor.fetchone()['n']
            return jsonify({
                'models': int(models),
                'valid': int(valid),
                'with_resolution': int(with_resolution),
            })
        except Exception as e:
            return jsonify({'error': str(e), 'models': 0, 'valid': 0, 'with_resolution': 0}), 500
        finally:
            cursor.close()


@app.route('/api/laptop-analytics')
@cache_control(max_age=60)
def laptop_analytics():
    """Aggregated analytics for the laptops page charts.

    Returns top brands, top CPUs, display-size distribution, and
    RAM-size distribution by listing count. Built off the listings
    table joined to laptop_reference for canonical brand/model and
    laptop_reference_cpu for canonical CPU.

    Filter-aware: accepts the same filter params as /api/laptops
    (brand, city, cpu_ref_id, gpu, min_price, max_price, ram_min,
    ram_max, storage_min, storage_max, storage_type, display_size,
    display_size_min, display_size_max, model, material,
    refresh_rate_min, macbook_only, exclude_macbooks) so the four
    charts reflect whatever the user has currently filtered the
    listings table to.

    Generic CPU rows (e.g. "Intel i5", "Intel i7" with no model
    number) are excluded from top_cpus — they crowd the chart with
    a single "i5" / "i7" bucket that lumps 60+ distinct models
    together. The user can still see the breakdown by clicking on
    the listings filtered to i5/i7 instead.
    """
    # ---- Parse filter params (mirrors /api/laptops) ----
    brand_filter = request.args.get('brand', '').strip()
    city_filter = request.args.get('city', '').strip()
    exclude_city_filter = request.args.get('exclude_city', '').strip()
    material_filter = request.args.get('material', '').strip().lower()
    refresh_rate_min = request.args.get('refresh_rate_min', '').strip()
    cpu_filter_list = request.args.getlist('cpu')
    cpu_ref_filter_list = request.args.getlist('cpu_ref_id')
    gpu_filter = request.args.get('gpu', '').strip()
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    ram_min = request.args.get('ram_min', '')
    ram_max = request.args.get('ram_max', '')
    storage_min = request.args.get('storage_min', '')
    storage_max = request.args.get('storage_max', '')
    storage_type = request.args.get('storage_type', '').strip()
    display_size = request.args.get('display_size', '').strip()
    display_size_min = request.args.get('display_size_min', '').strip()
    display_size_max = request.args.get('display_size_max', '').strip()
    model_filter = request.args.get('model', '').strip()
    include_macbooks = request.args.get('macbook_only', '').lower() == 'true'
    exclude_macbooks = request.args.get('exclude_macbooks', '').lower() == 'true'

    # Build a shared list of WHERE clauses that all four chart queries
    # reuse. All clauses are written against `l.*` (laptop_listings) and
    # `fl.*` (flagged_listings) so they slot into every query below.
    filter_clauses = ["l.is_active = true", "fl.listing_id IS NULL"]
    filter_params = []

    # Brand / Apple filters. The full set of combinations mirrors
    # /api/laptops so the two endpoints agree on what "show Dell only" or
    # "show macbooks" means:
    #   - include_macbooks AND brand_filter  → just the apple filter (brand is irrelevant)
    #   - exclude_macbooks AND brand_filter  → brand filter + NOT apple
    #   - brand_filter alone                 → brand filter only
    #   - include_macbooks alone             → apple filter
    #   - exclude_macbooks alone             → NOT apple
    if include_macbooks and brand_filter:
        filter_clauses.append("(l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
        filter_params.extend([f'%{brand_filter}%', '%apple%', '%macbook%', '%macbook%'])
    elif exclude_macbooks and brand_filter:
        filter_clauses.append("l.brand ILIKE %s")
        filter_params.append(f'%{brand_filter}%')
        filter_clauses.append("NOT (l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
        filter_params.extend(['%apple%', '%macbook%', '%macbook%'])
    elif brand_filter:
        filter_clauses.append("l.brand ILIKE %s")
        filter_params.append(f'%{brand_filter}%')
    elif include_macbooks:
        filter_clauses.append("(l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
        filter_params.extend(['%apple%', '%macbook%', '%macbook%'])
    elif exclude_macbooks:
        filter_clauses.append("NOT (l.brand ILIKE %s OR l.title ILIKE %s OR l.description ILIKE %s)")
        filter_params.extend(['%apple%', '%macbook%', '%macbook%'])

    if cpu_filter_list:
        cleaned = [c.strip() for c in cpu_filter_list if c.strip()]
        if cleaned:
            or_clauses = []
            for val in cleaned:
                or_clauses.append("l.cpu_raw ILIKE %s")
                filter_params.append(f'%{val}%')
            filter_clauses.append("(" + " OR ".join(or_clauses) + ")")

    if cpu_ref_filter_list:
        cleaned_ids = [int(c) for c in cpu_ref_filter_list if c.strip().isdigit()]
        if cleaned_ids:
            filter_clauses.append("l.cpu_reference_id = ANY(%s)")
            filter_params.append(cleaned_ids)

    if gpu_filter:
        filter_clauses.append("l.gpu_raw ILIKE %s")
        filter_params.append(f'%{gpu_filter}%')
    if min_price:
        try:
            filter_clauses.append("l.price_eur >= %s")
            filter_params.append(float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            filter_clauses.append("l.price_eur <= %s")
            filter_params.append(float(max_price))
        except ValueError:
            pass
    if ram_min:
        try:
            filter_clauses.append("l.ram_gb >= %s")
            filter_params.append(int(ram_min))
        except ValueError:
            pass
    if ram_max:
        try:
            filter_clauses.append("l.ram_gb <= %s")
            filter_params.append(int(ram_max))
        except ValueError:
            pass
    if storage_min:
        try:
            filter_clauses.append("l.storage_gb >= %s")
            filter_params.append(int(storage_min))
        except ValueError:
            pass
    if storage_max:
        try:
            filter_clauses.append("l.storage_gb <= %s")
            filter_params.append(int(storage_max))
        except ValueError:
            pass
    if storage_type:
        filter_clauses.append("l.storage_type ILIKE %s")
        filter_params.append(f'%{storage_type}%')
    if display_size:
        try:
            filter_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric = %s")
            filter_params.append(float(display_size))
        except ValueError:
            pass
    if display_size_min:
        try:
            filter_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric >= %s")
            filter_params.append(float(display_size_min))
        except ValueError:
            pass
    if display_size_max:
        try:
            filter_clauses.append("NULLIF(REGEXP_REPLACE(l.display_size, '[^0-9.]', '', 'g'), '')::numeric <= %s")
            filter_params.append(float(display_size_max))
        except ValueError:
            pass
    if model_filter:
        filter_clauses.append("l.model ILIKE %s")
        filter_params.append(f'%{model_filter}%')
    if city_filter:
        filter_clauses.append("l.seller_location = %s")
        filter_params.append(city_filter)
    if exclude_city_filter:
        filter_clauses.append("(l.seller_location IS NULL OR l.seller_location <> %s)")
        filter_params.append(exclude_city_filter)
    if material_filter:
        filter_clauses.append("l.material ILIKE %s")
        filter_params.append(f'%{material_filter}%')
    if refresh_rate_min:
        try:
            filter_clauses.append("l.refresh_rate_hz >= %s")
            filter_params.append(int(refresh_rate_min))
        except ValueError:
            pass

    # All four queries use `l.*` (laptop_listings) + `fl.*` (flagged_listings)
    # as the FROM anchors; the filter SQL below is appended identically.
    filter_sql = " AND ".join(filter_clauses)

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Top brands by listing count + avg price
            cursor.execute(f"""
                SELECT
                    COALESCE(lr.brand, l.brand) AS brand,
                    COUNT(l.listing_id) AS listing_count,
                    AVG(l.price_eur)::numeric(10, 2) AS avg_price,
                    MIN(l.price_eur) AS min_price,
                    MAX(l.price_eur) AS max_price
                FROM laptop_listings l
                LEFT JOIN laptop_reference lr ON l.laptop_reference_id = lr.id
                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id AND fl.category = 'laptop'
                WHERE {filter_sql}
                  AND COALESCE(lr.brand, l.brand) IS NOT NULL
                  AND COALESCE(lr.brand, l.brand) <> ''
                GROUP BY COALESCE(lr.brand, l.brand)
                ORDER BY listing_count DESC
                LIMIT 12
            """, filter_params)
            top_brands = [
                {
                    'brand': r['brand'],
                    'count': int(r['listing_count']),
                    'avg_price': float(r['avg_price']) if r['avg_price'] else 0,
                    'min_price': float(r['min_price']) if r['min_price'] else 0,
                    'max_price': float(r['max_price']) if r['max_price'] else 0,
                }
                for r in cursor.fetchall()
            ]

            # Top CPUs by listing count (joined to laptop_reference_cpu for
            # canonical model). The chart shows the top 15 SPECIFIC models
            # (e.g. "i5-7300U", "Ryzen 5 5600X") so the user can see real
            # breakdowns. Generic tier rows like "Intel i5" or "Intel i7"
            # are excluded — they crowd the chart with one big bucket that
            # hides the actual variety.
            cursor.execute(f"""
                SELECT
                    lrc.brand AS cpu_brand,
                    lrc.model AS cpu_model,
                    COUNT(l.listing_id) AS listing_count,
                    AVG(l.price_eur)::numeric(10, 2) AS avg_price
                FROM laptop_listings l
                JOIN laptop_reference_cpu lrc ON l.cpu_reference_id = lrc.id
                LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id AND fl.category = 'laptop'
                WHERE {filter_sql}
                  AND lrc.model IS NOT NULL AND lrc.model <> ''
                  AND NOT (lrc.brand = 'Intel' AND lrc.model IN ('i3', 'i5', 'i7', 'i9'))
                GROUP BY lrc.brand, lrc.model
                ORDER BY listing_count DESC
                LIMIT 15
            """, filter_params)
            top_cpus = [
                {
                    'cpu_brand': r['cpu_brand'],
                    'cpu_model': r['cpu_model'],
                    'label': f"{r['cpu_brand']} {r['cpu_model']}" if r['cpu_brand'] else r['cpu_model'],
                    'count': int(r['listing_count']),
                    'avg_price': float(r['avg_price']) if r['avg_price'] else 0,
                }
                for r in cursor.fetchall()
            ]

            # Display size distribution (group 17+ together).
            # `display_size` is a text column (e.g. "15.6", "14"), so we cast
            # to numeric for the comparison and trim before casting so "15.6""
            # doesn't break the parse.
            display_params = list(filter_params)  # params for the OUTER query
            cursor.execute(f"""
                WITH bucketed AS (
                    SELECT
                        CASE
                            WHEN l.display_size IS NULL OR l.display_size = '' OR NULLIF(regexp_replace(l.display_size, '[^0-9.]', '', 'g'), '')::numeric = 0 THEN 'Unknown'
                            WHEN regexp_replace(l.display_size, '[^0-9.]', '', 'g')::numeric < 13 THEN '11-12"'
                            WHEN regexp_replace(l.display_size, '[^0-9.]', '', 'g')::numeric < 14 THEN '13"'
                            WHEN regexp_replace(l.display_size, '[^0-9.]', '', 'g')::numeric < 15 THEN '14"'
                            WHEN regexp_replace(l.display_size, '[^0-9.]', '', 'g')::numeric < 16 THEN '15"'
                            WHEN regexp_replace(l.display_size, '[^0-9.]', '', 'g')::numeric < 17 THEN '16"'
                            ELSE '17"+'
                        END AS size_bucket,
                        l.price_eur
                    FROM laptop_listings l
                    LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id AND fl.category = 'laptop'
                    WHERE {filter_sql}
                )
                SELECT
                    size_bucket,
                    COUNT(*) AS listing_count,
                    AVG(price_eur)::numeric(10, 2) AS avg_price
                FROM bucketed
                GROUP BY size_bucket
                ORDER BY
                    CASE size_bucket
                        WHEN '11-12"' THEN 1
                        WHEN '13"' THEN 2
                        WHEN '14"' THEN 3
                        WHEN '15"' THEN 4
                        WHEN '16"' THEN 5
                        WHEN '17"+' THEN 6
                        ELSE 7
                    END
            """, filter_params)
            display_buckets = [
                {
                    'bucket': r['size_bucket'],
                    'count': int(r['listing_count']),
                    'avg_price': float(r['avg_price']) if r['avg_price'] else 0,
                }
                for r in cursor.fetchall()
            ]

            # RAM size distribution
            cursor.execute(f"""
                WITH bucketed AS (
                    SELECT
                        CASE
                            WHEN l.ram_gb IS NULL OR l.ram_gb = 0 THEN 'Unknown'
                            WHEN l.ram_gb <= 4 THEN '4 GB'
                            WHEN l.ram_gb <= 8 THEN '8 GB'
                            WHEN l.ram_gb <= 16 THEN '16 GB'
                            WHEN l.ram_gb <= 32 THEN '32 GB'
                            ELSE '64+ GB'
                        END AS ram_bucket,
                        l.price_eur
                    FROM laptop_listings l
                    LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id AND fl.category = 'laptop'
                    WHERE {filter_sql}
                )
                SELECT
                    ram_bucket,
                    COUNT(*) AS listing_count,
                    AVG(price_eur)::numeric(10, 2) AS avg_price
                FROM bucketed
                GROUP BY ram_bucket
                ORDER BY
                    CASE ram_bucket
                        WHEN '4 GB' THEN 1
                        WHEN '8 GB' THEN 2
                        WHEN '16 GB' THEN 3
                        WHEN '32 GB' THEN 4
                        WHEN '64+ GB' THEN 5
                        ELSE 6
                    END
            """, filter_params)
            ram_buckets = [
                {
                    'bucket': r['ram_bucket'],
                    'count': int(r['listing_count']),
                    'avg_price': float(r['avg_price']) if r['avg_price'] else 0,
                }
                for r in cursor.fetchall()
            ]

            return jsonify({
                'top_brands': top_brands,
                'top_cpus': top_cpus,
                'display_buckets': display_buckets,
                'ram_buckets': ram_buckets,
            })
        except Exception as e:
            return jsonify({
                'error': str(e),
                'top_brands': [],
                'top_cpus': [],
                'display_buckets': [],
                'ram_buckets': [],
            }), 500
        finally:
            cursor.close()


@app.route('/api/laptop-reference/save', methods=['POST'])
@require_login
@require_role('mod')
def save_laptop_reference():
    """Create or update laptop reference specs (material, port counts, resolution).

    Requires mod or admin. The row is keyed by normalized brand+model+size, so a
    single save propagates to every laptop listing with the same combo.
    The VALID mark (is_valid) may only be changed by admins.
    """
    user = g.get('current_user')
    data = request.get_json(silent=True) or {}

    brand = str(data.get('brand') or '').strip()
    model = str(data.get('model') or '').strip()
    # Optional model number / SKU (e.g. "A515-58P" for "Aspire 5"). NULL
    # means "no SKU / admin hasn't filled it in yet". Not used in the
    # normalized_key — lookups still go by (brand, model, display_size).
    model_number = (str(data.get('model_number') or '').strip() or None)
    if model_number and len(model_number) > 64:
        return jsonify({'error': 'model_number is too long'}), 400
    display_size = str(data.get('display_size') or '').strip()
    if not brand or not model:
        return jsonify({'error': 'brand and model are required'}), 400

    material = data.get('material')
    if material in ('', None):
        material = None
    else:
        material = str(material).strip().capitalize()
        if material not in ('Plastic', 'Metal'):
            return jsonify({'error': 'material must be "Plastic" or "Metal"'}), 400

    def _parse_count(name):
        val = data.get(name)
        if val in (None, ''):
            return None
        try:
            n = int(val)
        except (TypeError, ValueError):
            raise ValueError(f'{name} must be an integer')
        if not 0 <= n <= 20:
            raise ValueError(f'{name} must be between 0 and 20')
        return n

    try:
        usb_c_count = _parse_count('usb_c_count')
        usb_count = _parse_count('usb_count')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Yes/no feature flags. The frontend uses 3-state values ('true' / 'false' /
    # absent); absent means "no change" on UPDATE, NULL on INSERT.
    def _parse_bool(name):
        if name not in data:
            return None  # No change on UPDATE; NULL on INSERT handled below
        v = data.get(name)
        if v in (None, '', 'null'):
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    has_hdmi = _parse_bool('has_hdmi')
    has_video_pd_usb_c = _parse_bool('has_video_pd_usb_c')
    has_ethernet = _parse_bool('has_ethernet')
    has_touchscreen = _parse_bool('has_touchscreen')

    # Refresh rate: small int (Hz). NULL clears it.
    refresh_rate_hz = None
    if 'refresh_rate_hz' in data:
        raw = data.get('refresh_rate_hz')
        if raw in (None, '', 'null'):
            refresh_rate_hz = None
        else:
            try:
                refresh_rate_hz = int(raw)
                if not 30 <= refresh_rate_hz <= 1000:
                    return jsonify({'error': 'refresh_rate_hz must be between 30 and 1000'}), 400
            except (TypeError, ValueError):
                return jsonify({'error': 'refresh_rate_hz must be an integer'}), 400

    # Legacy hdmi_count is now derived from has_hdmi. Keep the column for
    # back-compat but stop exposing it as an editable input.
    hdmi_count = 1 if has_hdmi else 0 if has_hdmi is not None else None

    resolution = str(data.get('resolution') or '').strip() or None
    if resolution and len(resolution) > 32:
        return jsonify({'error': 'resolution is too long'}), 400

    # VALID mark is admin-only; ignore silently for mods (UI hides it anyway).
    set_is_valid = None
    if user['role'] == 'admin' and 'is_valid' in data:
        set_is_valid = bool(data.get('is_valid'))

    normalized_key = (
        re.sub(r'\s+', ' ', brand.lower()) + '|' +
        re.sub(r'\s+', ' ', model.lower()) + '|' +
        re.sub(r'[^0-9.]', '', display_size)
    )

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Note: on INSERT we honour whatever the caller passed (NULL when not
            # provided); on UPDATE we re-write all editable columns with the
            # supplied values (NULL clears).
            if set_is_valid is None:
                base_sql = """
                    INSERT INTO laptop_reference
                        (brand, model, model_number, display_size, normalized_key, material,
                         usb_c_count, usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                         has_ethernet, has_touchscreen, refresh_rate_hz, resolution)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (normalized_key) DO UPDATE SET
                        model_number = EXCLUDED.model_number,
                        material = EXCLUDED.material,
                        usb_c_count = EXCLUDED.usb_c_count,
                        usb_count = EXCLUDED.usb_count,
                        hdmi_count = EXCLUDED.hdmi_count,
                        has_hdmi = EXCLUDED.has_hdmi,
                        has_video_pd_usb_c = EXCLUDED.has_video_pd_usb_c,
                        has_ethernet = EXCLUDED.has_ethernet,
                        has_touchscreen = EXCLUDED.has_touchscreen,
                        refresh_rate_hz = EXCLUDED.refresh_rate_hz,
                        resolution = EXCLUDED.resolution,
                        updated_at = NOW()
                    RETURNING id, brand, model, model_number, display_size, material, usb_c_count,
                              usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                              has_ethernet, has_touchscreen, refresh_rate_hz,
                              resolution, is_valid
                """
                params = [brand, model, model_number, display_size or None, normalized_key, material,
                          usb_c_count, usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                          has_ethernet, has_touchscreen, refresh_rate_hz, resolution]
                sql = base_sql
            else:
                sql = """
                    INSERT INTO laptop_reference
                        (brand, model, model_number, display_size, normalized_key, material,
                         usb_c_count, usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                         has_ethernet, has_touchscreen, refresh_rate_hz, resolution, is_valid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (normalized_key) DO UPDATE SET
                        model_number = EXCLUDED.model_number,
                        material = EXCLUDED.material,
                        usb_c_count = EXCLUDED.usb_c_count,
                        usb_count = EXCLUDED.usb_count,
                        hdmi_count = EXCLUDED.hdmi_count,
                        has_hdmi = EXCLUDED.has_hdmi,
                        has_video_pd_usb_c = EXCLUDED.has_video_pd_usb_c,
                        has_ethernet = EXCLUDED.has_ethernet,
                        has_touchscreen = EXCLUDED.has_touchscreen,
                        refresh_rate_hz = EXCLUDED.refresh_rate_hz,
                        resolution = EXCLUDED.resolution,
                        is_valid = EXCLUDED.is_valid,
                        updated_at = NOW()
                    RETURNING id, brand, model, model_number, display_size, material, usb_c_count,
                              usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                              has_ethernet, has_touchscreen, refresh_rate_hz,
                              resolution, is_valid
                """
                params = [brand, model, model_number, display_size or None, normalized_key, material,
                          usb_c_count, usb_count, hdmi_count, has_hdmi, has_video_pd_usb_c,
                          has_ethernet, has_touchscreen, refresh_rate_hz, resolution,
                          set_is_valid]
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            conn.commit()
            return jsonify({'ok': True, 'reference': convert_decimal_to_float(dict(row))})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()

@app.route('/wiki')
@require_role('admin')
def wiki_page():
    """Render the browsable project wiki from docs/project_wiki.md."""
    wiki_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'project_wiki.md')
    if os.path.exists(wiki_path):
        with open(wiki_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        if _markdown:
            md_converter = _markdown.Markdown(extensions=['toc', 'tables', 'fenced_code'])
            html_content = md_converter.convert(md_content)
            toc_html = md_converter.toc
        else:
            html_content = f"<pre>{md_content}</pre>"
            toc_html = ""
    else:
        html_content = "<p>Wiki not found.</p>"
        toc_html = ""
    return render_template('wiki.html', wiki_html=html_content, toc_html=toc_html, title="Project Wiki")




@app.route('/healthz')
def healthz():
    """Health check endpoint that exercises the connection pool."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Use the tornado WSGI server via start_tornado.py. Werkzeug's dev
    # server has two known issues on Windows: (1) the auto-reloader
    # randomly kills the worker on any file change under the project
    # (including jinja2/filters.py in site-packages), and (2) IPv4-only
    # binding makes `localhost` (which resolves to ::1 on Windows) take
    # ~2s per request as it falls back to IPv4. tornado binds both
    # IPv4 and IPv6, has no auto-reloader, and is faster.
    #
    # Delegating here means the old `python app.py` command keeps
    # working — it just transparently hands off to the tornado server.
    import subprocess
    import sys as _sys
    import os as _os
    import socket as _socket
    here = _os.path.dirname(_os.path.abspath(__file__))

    # Detect an already-running server on :5000 and bail out with a
    # helpful message instead of the cryptic "WinError 10048" you'd
    # get from tornado's bind_sockets.
    def _port_in_use(port):
        for fam in (_socket.AF_INET, _socket.AF_INET6):
            try:
                s = _socket.socket(fam, _socket.SOCK_STREAM)
                s.settimeout(0.2)
                if fam == _socket.AF_INET:
                    s.connect(('127.0.0.1', port))
                else:
                    s.connect(('::1', port))
                s.close()
                return True
            except OSError:
                continue
            finally:
                try: s.close()
                except Exception: pass
        return False

    if _port_in_use(5000):
        sys.stderr.write(
            'SS-WEBSITE is already running on http://localhost:5000\n'
            '  To stop it:  powershell -File stop_server.ps1\n'
            '  To restart: powershell -File stop_server.ps1; py app.py\n'
        )
        raise SystemExit(0)

    # Top-of-file code already populated os.environ['FLASK_SECRET_KEY']
    # with the dev fallback if it wasn't set. Just inherit it.
    raise SystemExit(subprocess.call([_sys.executable, _os.path.join(here, 'start_tornado.py')]))


