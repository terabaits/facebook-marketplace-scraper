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
    """Get GPU listings with filters."""
    try:
        conn = get_db_connection()
    except Exception as e:
        return jsonify({'error': f'Database connection failed: {str(e)}'}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get query parameters
    show_active = request.args.get('active', 'true').lower() == 'true'
    min_confidence = float(request.args.get('min_confidence', 0))
    
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
    
    query += " ORDER BY l.date_posted DESC LIMIT 100"
    
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
        
        # Enhance listings with price comparison
        enhanced_listings = []
        for listing in listings:
            listing_dict = dict(listing)
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
    
    query += " ORDER BY l.date_posted DESC LIMIT 100"
    
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


@app.route('/api/gpu-models')
def get_gpu_models():
    """Get aggregated GPU model statistics."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
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
        GROUP BY g.id, g.vendor, g.model, g.vram_gb, g.year_released
        HAVING COUNT(l.id) >= 1
        ORDER BY avg_price DESC
    """)
    
    models = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in models])


@app.route('/api/cpu-models')
def get_cpu_models():
    """Get aggregated CPU model statistics."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
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
        GROUP BY c.id, c.producer, c.cpu_name, c.processor_number, c.cores, c.threads, c.socket
        HAVING COUNT(l.id) >= 1
        ORDER BY avg_price DESC
    """)
    
    models = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify([dict(row) for row in models])


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
