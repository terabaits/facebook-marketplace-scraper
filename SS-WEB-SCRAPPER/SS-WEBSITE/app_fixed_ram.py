#!/usr/bin/env python3
"""SS-Crawler Web Dashboard - View scraped GPU/CPU data with statistics."""
import os
from datetime import datetime, timedelta
from typing import Optional
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 5433)),
    'database': os.environ.get('DATABASE_NAME', 'ss_market'),
    'user': os.environ.get('DATABASE_USER', 'crawler'),
    'password': os.environ.get('DATABASE_PASSWORD', 'crawler_pass')
}


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_category_latest_import_date(category):
    """Get the latest import date for a specific category."""
    conn = get_db_connection()
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
        conn.close()


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
IMAGE_FOLDERS = {
    'facebook': 'G:/Github/SS-WEB-SCRAPPER/images/facebook',
    'gpu': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/gpus',  # singular key for backward compat
    'gpus': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/gpus',
    'cpu': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/cpus',
    'cpus': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/cpus',
    'ram': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/rams',
    'rams': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/rams',
    'ssd': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/ssds',
    'ssds': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/ssds',
    'consoles': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/consoles',
    'monitors': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/monitors',
    'cases': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/cases',
    'cameras': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/cameras',
    'lenses': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/lenses',
    'psu': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu',
    'motherboards': 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/motherboards',
}

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from the external images folders."""
    from flask import send_from_directory, abort
    import os
    
    # Normalize path separators (handle Windows backslashes)
    filename = filename.replace('\\', '/')
    
    # Determine which folder to use based on filename prefix
    # local_image_path format: "facebook/filename.jpg" or "gpus/filename.jpg" etc.
    folder_key = None
    actual_filename = filename
    
    for key in IMAGE_FOLDERS:
        if filename.startswith(f"{key}/"):
            folder_key = key
            actual_filename = filename[len(key)+1:]  # Remove the folder prefix
            break
    
    if folder_key and folder_key in IMAGE_FOLDERS:
        folder = IMAGE_FOLDERS[folder_key]
    else:
        # Fallback: try to find in any folder
        for folder in IMAGE_FOLDERS.values():
            full_path = os.path.join(folder, filename)
            if os.path.exists(full_path):
                folder = os.path.dirname(full_path)
                actual_filename = os.path.basename(filename)
                return send_from_directory(folder, actual_filename)
        return abort(404)
    
    return send_from_directory(folder, actual_filename)


def format_vram(vram_mb):
    """Convert VRAM from MB to GB for display."""
    if vram_mb is None:
        return None
    return round(vram_mb / 1024)


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
    if time_filter == 'week':
        return f" AND {table_alias}.date_posted > NOW() - INTERVAL '7 days'"
    elif time_filter == 'month':
        return f" AND {table_alias}.date_posted > NOW() - INTERVAL '30 days'"
    return ""  # all_time


@app.route('/')
def index():
    """Dashboard homepage."""
    return render_template('index.html')


@app.route('/api/category-earnings')
def get_category_earnings():
    """Get earnings/revenue data by category."""
    conn = get_db_connection()
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
            'totals': totals,
            'by_category': [dict(row) for row in earnings]
        }
