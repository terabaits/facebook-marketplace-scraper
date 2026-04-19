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


def format_vram(vram_mb):
    """Convert VRAM from MB to GB for display."""
    if vram_mb is None:
        return None
    return round(vram_mb / 1024)


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


@app.route('/api/stats')
def get_stats():
    """Get overall statistics."""
    conn = get_db_connection()
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
    conn.close()
    
    return jsonify(stats)


@app.route('/api/gpus')
def get_gpus():
    """Get GPU listings with filters and sorting."""
    try:
        conn = get_db_connection()
    except Exception as e:
        return jsonify({'error': f'Database connection failed: {str(e)}'}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get query parameters
    show_active = request.args.get('active', 'true').lower() == 'true'
    min_confidence = float(request.args.get('min_confidence', 0))
    time_filter = request.args.get('time', 'all_time')  # week, month, all_time
    sort_by = request.args.get('sort', 'date_posted')  # price, date_posted
    sort_order = request.args.get('order', 'desc')  # asc, desc
    
    query = """
        SELECT 
            l.listing_id,
            l.title,
            l.price_eur,
            l.seller_location,
            l.date_posted,
            l.is_active,
            l.confidence_score,
            l.match_method,
            l.matched_gpu_id,
            g.vendor,
            g.model as gpu_model,
            g.vram_gb,
            g.year_released,
            l.image_url,
            l.listing_url
        FROM listings l
        LEFT JOIN gpu_reference g ON l.matched_gpu_id = g.id
        WHERE l.category = 'gpu'
    """
    
    params = []
    if show_active:
        query += " AND l.is_active = true"
    if min_confidence > 0:
        query += " AND l.confidence_score >= %s"
        params.append(min_confidence)
    
    # Add time filter
    query += get_time_filter_sql(time_filter)
    
    # Add sorting
    sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
    sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
    query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"
    
    try:
        cursor.execute(query, params)
        listings = cursor.fetchall()
        
        # Add price statistics for each GPU model
        gpu_stats = {}
        cursor.execute("""
            SELECT 
                g.id,
                g.vendor,
                g.model,
                ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price,
                COUNT(*) as listing_count
            FROM listings l
            JOIN gpu_reference g ON l.matched_gpu_id = g.id
            WHERE l.category = 'gpu' AND l.is_active = true
            GROUP BY g.id, g.vendor, g.model
            HAVING COUNT(*) >= 2
        """)
        for row in cursor.fetchall():
            gpu_stats[row['id']] = dict(row)
        
        # Enhance listings with price comparison and format VRAM
        enhanced_listings = []
        for listing in listings:
            listing_dict = dict(listing)
            # Format VRAM from MB to GB
            if listing_dict.get('vram_gb'):
                listing_dict['vram_gb'] = format_vram(listing_dict['vram_gb'])
            if listing['matched_gpu_id'] and listing['matched_gpu_id'] in gpu_stats:
                stats = gpu_stats[listing['matched_gpu_id']]
                listing_dict['price_stats'] = {
                    'avg': stats['avg_price'],
                    'min': stats['min_price'],
                    'max': stats['max_price'],
                    'below_avg': listing['price_eur'] < stats['avg_price'],
                    'percentile': round((listing['price_eur'] - stats['min_price']) / 
                                      (stats['max_price'] - stats['min_price']) * 100, 1) 
                                      if stats['max_price'] > stats['min_price'] else 50
                }
            enhanced_listings.append(listing_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify(enhanced_listings)
        
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cpus')
def get_cpus():
    """Get CPU listings with filters."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    show_active = request.args.get('active', 'true').lower() == 'true'
    min_confidence = float(request.args.get('min_confidence', 0))
    time_filter = request.args.get('time', 'all_time')
    sort_by = request.args.get('sort', 'date_posted')
    sort_order = request.args.get('order', 'desc')
    
    query = """
        SELECT 
            l.listing_id,
            l.title,
            l.price_eur,
            l.seller_location,
            l.date_posted,
            l.is_active,
            l.cpu_confidence_score as confidence_score,
            l.cpu_match_method as match_method,
            l.matched_cpu_id,
            c.producer,
            c.cpu_name,
            c.processor_number,
            c.cores,
            c.threads,
            c.socket,
            c.base_freq,
            l.image_url,
            l.listing_url
        FROM listings l
        LEFT JOIN cpu_reference c ON l.matched_cpu_id = c.id
        WHERE l.category = 'cpu'
    """
    
    params = []
    if show_active:
        query += " AND l.is_active = true"
    if min_confidence > 0:
        query += " AND l.cpu_confidence_score >= %s"
        params.append(min_confidence)
    
    query += get_time_filter_sql(time_filter)
    
    sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
    sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
    query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"
    
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
        HAVING COUNT(*) >= 2
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
                                  if stats['max_price'] > stats['min_price'] else 50
            }
        enhanced_listings.append(listing_dict)
    
    cursor.close()
    conn.close()
    
    return jsonify(enhanced_listings)


@app.route('/api/price-history/<listing_id>')
def get_price_history(listing_id):
    """Get price history for a specific listing."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT price_eur, recorded_at
        FROM price_history
        WHERE listing_id = %s
        ORDER BY recorded_at ASC
    """, (listing_id,))
    
    history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in history])


@app.route('/api/model-history/<model_type>/<int:model_id>')
def get_model_history(model_type, model_id):
    """Get all historical prices for a specific model."""
    conn = get_db_connection()
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
                l.listing_url
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
                l.listing_url
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
                l.listing_url
            FROM listings l
            WHERE l.matched_cpu_id = %s AND l.category = 'cpu'
            ORDER BY l.date_posted DESC
        """, (model_id,))
    
    listings = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in listings])


@app.route('/api/gpu-models')
def get_gpu_models():
    """Get aggregated GPU model statistics with sorting."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    sort = request.args.get('sort', 'price_desc')
    time_filter = request.args.get('time', 'all_time')
    
    # Build ORDER BY clause
    order_map = {
        'price_desc': 'avg_price DESC',
        'price_asc': 'avg_price ASC',
        'listings_desc': 'active_listings DESC',
        'listings_asc': 'active_listings ASC'
    }
    order_by = order_map.get(sort, 'avg_price DESC')
    
    time_clause = get_time_filter_sql(time_filter, 'l')
    
    cursor.execute(f"""
        SELECT 
            g.id,
            g.vendor,
            g.model,
            g.vram_gb,
            g.year_released,
            COUNT(l.id) as active_listings,
            ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
            MIN(l.price_eur) as min_price,
            MAX(l.price_eur) as max_price,
            MIN(l.date_posted) as first_seen,
            MAX(l.date_posted) as last_seen
        FROM gpu_reference g
        JOIN listings l ON g.id = l.matched_gpu_id
        WHERE l.category = 'gpu' 
            AND l.is_active = true
            AND l.confidence_score >= 0.70
            {time_clause}
        GROUP BY g.id, g.vendor, g.model, g.vram_gb, g.year_released
        HAVING COUNT(l.id) >= 1
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
    conn.close()
    
    return jsonify(formatted_models)


@app.route('/api/cpu-models')
def get_cpu_models():
    """Get aggregated CPU model statistics with sorting."""
    conn = get_db_connection()
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
    
    time_clause = get_time_filter_sql(time_filter, 'l')
    
    cursor.execute(f"""
        SELECT 
            c.id,
            c.producer,
            c.cpu_name,
            c.processor_number,
            c.cores,
            c.threads,
            c.socket,
            COUNT(l.id) as active_listings,
            ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
            MIN(l.price_eur) as min_price,
            MAX(l.price_eur) as max_price
        FROM cpu_reference c
        JOIN listings l ON c.id = l.matched_cpu_id
        WHERE l.category = 'cpu' 
            AND l.is_active = true
            AND l.cpu_confidence_score >= 0.70
            {time_clause}
        GROUP BY c.id, c.producer, c.cpu_name, c.processor_number, c.cores, c.threads, c.socket
        HAVING COUNT(l.id) >= 1
        ORDER BY {order_by}
    """)
    
    models = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in models])


@app.route('/api/ssd-models')
def get_ssd_models():
    """Get aggregated SSD model statistics with sorting."""
    conn = get_db_connection()
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
    
    time_clause = get_time_filter_sql(time_filter, 'l')
    
    cursor.execute(f"""
        SELECT 
            s.id,
            s.brand,
            s.model,
            s.capacity_gb,
            s.interface,
            s.form_factor,
            COUNT(l.id) as active_listings,
            ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
            MIN(l.price_eur) as min_price,
            MAX(l.price_eur) as max_price,
            MIN(l.date_posted) as first_seen,
            MAX(l.date_posted) as last_seen
        FROM ssd_reference s
        JOIN listings l ON s.id = l.matched_ssd_id
        WHERE l.category = 'ssd' 
            AND l.is_active = true
            AND l.ssd_confidence_score >= 0.70
            {time_clause}
        GROUP BY s.id, s.brand, s.model, s.capacity_gb, s.interface, s.form_factor
        HAVING COUNT(l.id) >= 1
        ORDER BY {order_by}
    """)
    
    models = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in models])


@app.route('/api/ssds')
def get_ssds():
    """Get SSD listings with filters and sorting."""
    try:
        conn = get_db_connection()
    except Exception as e:
        return jsonify({'error': f'Database connection failed: {str(e)}'}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get query parameters
    show_active = request.args.get('active', 'true').lower() == 'true'
    min_confidence = float(request.args.get('min_confidence', 0))
    time_filter = request.args.get('time', 'all_time')
    sort_by = request.args.get('sort', 'date_posted')
    sort_order = request.args.get('order', 'desc')
    
    query = """
        SELECT 
            l.listing_id,
            l.title,
            l.price_eur,
            l.seller_location,
            l.date_posted,
            l.is_active,
            l.ssd_confidence_score,
            l.ssd_match_method,
            l.matched_ssd_id,
            l.capacity_gb,
            s.brand as ssd_brand,
            s.model as ssd_model,
            s.interface,
            s.form_factor,
            l.image_url,
            l.listing_url
        FROM listings l
        LEFT JOIN ssd_reference s ON l.matched_ssd_id = s.id
        WHERE l.category = 'ssd'
    """
    
    params = []
    if show_active:
        query += " AND l.is_active = true"
    if min_confidence > 0:
        query += " AND l.ssd_confidence_score >= %s"
        params.append(min_confidence)
    
    query += get_time_filter_sql(time_filter)
    
    sort_column = 'l.price_eur' if sort_by == 'price' else 'l.date_posted'
    sort_dir = 'ASC' if sort_order == 'asc' else 'DESC'
    query += f" ORDER BY {sort_column} {sort_dir} LIMIT 100"
    
    try:
        cursor.execute(query, params)
        listings = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify([dict(row) for row in listings])
        
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/ssd')
def ssd_page():
    """SSD listings page."""
    return render_template('ssd.html')


@app.route('/api/unmatched')
def get_unmatched():
    """Get unmatched listings that need manual review."""
    conn = get_db_connection()
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
    conn.close()
    
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
    
    conn = get_db_connection()
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
        conn.close()
        
        return jsonify({'success': True, 'message': 'Listing updated successfully'})
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/gpu')
def gpu_page():
    """GPU listings page."""
    return render_template('gpu.html')


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
