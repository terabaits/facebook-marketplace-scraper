"""Web dashboard for SS-Crawler computer listings."""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository
)
from src.database.computer_repository import ComputerRepository
from src.models.computer_schemas import FlagData
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger("web_app")
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

config = AppConfig.from_yaml()
init_database(config.database)


@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@app.route('/computers')
def computers_page():
    """Computer listings dashboard."""
    return render_template('computers.html')


@app.route('/api/computers', methods=['GET'])
def get_computers():
    """Get all computer listings."""
    try:
        with get_session() as session:
            active_only = request.args.get('active', 'true').lower() == 'true'
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            listings = ComputerRepository.get_all(session, active_only, limit, offset)
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': [listing.model_dump() for listing in listings]
            })
    except Exception as e:
        logger.error(f"Error fetching computers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/<listing_id>', methods=['GET'])
def get_computer_detail(listing_id):
    """Get detailed computer listing with component breakdown."""
    try:
        with get_session() as session:
            listing = ComputerRepository.get_by_id(session, listing_id)
            if not listing:
                return jsonify({'success': False, 'error': 'Listing not found'}), 404
            
            # Get component breakdown
            breakdown = ComputerRepository.get_component_breakdown(
                session, listing_id,
                CPUReferenceRepository, GPUReferenceRepository,
                RAMReferenceRepository, SSDReferenceRepository,
                PSURepository, CaseRepository
            )
            
            result = {
                'success': True,
                'listing': listing.model_dump(),
                'breakdown': breakdown.model_dump() if breakdown else None
            }
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching computer detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/<listing_id>/flag', methods=['POST'])
def flag_computer(listing_id):
    """Flag a computer listing."""
    try:
        data = request.get_json()
        flag_data = FlagData(
            is_flagged=data.get('is_flagged', True),
            flag_reason=data.get('flag_reason'),
            flag_comment=data.get('flag_comment'),
            flagged_by=data.get('flagged_by', 'web_user')
        )
        
        with get_session() as session:
            success = ComputerRepository.flag_listing(session, listing_id, flag_data)
            if success:
                session.commit()
                return jsonify({'success': True, 'message': 'Listing flagged successfully'})
            else:
                return jsonify({'success': False, 'error': 'Failed to flag listing'}), 500
    except Exception as e:
        logger.error(f"Error flagging computer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/flagged', methods=['GET'])
def get_flagged_computers():
    """Get all flagged listings."""
    try:
        with get_session() as session:
            limit = int(request.args.get('limit', 100))
            listings = ComputerRepository.get_flagged(session, limit)
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': [listing.model_dump() for listing in listings]
            })
    except Exception as e:
        logger.error(f"Error fetching flagged computers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/search', methods=['GET'])
def search_computers():
    """Search computer listings."""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'error': 'Query parameter required'}), 400
        
        with get_session() as session:
            listings = ComputerRepository.search(session, query)
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': [listing.model_dump() for listing in listings]
            })
    except Exception as e:
        logger.error(f"Error searching computers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/computers/stats', methods=['GET'])
def get_computer_stats():
    """Get computer listings statistics."""
    try:
        with get_session() as session:
            stats = ComputerRepository.get_stats(session)
            return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/components', methods=['GET'])
def get_components():
    """Get all components for reference."""
    try:
        component_type = request.args.get('type', 'all')
        
        with get_session() as session:
            result = {}
            
            if component_type in ['all', 'cpu']:
                cpus = CPUReferenceRepository.get_all(session)
                result['cpus'] = [c.model_dump() for c in cpus]
            
            if component_type in ['all', 'gpu']:
                gpus = GPUReferenceRepository.get_all(session)
                result['gpus'] = [g.model_dump() for g in gpus]
            
            if component_type in ['all', 'ram']:
                rams = RAMReferenceRepository.get_all(session)
                result['rams'] = [r.model_dump() for r in rams]
            
            if component_type in ['all', 'ssd']:
                ssds = SSDReferenceRepository.get_all(session)
                result['ssds'] = [s.model_dump() for s in ssds]
            
            if component_type in ['all', 'psu']:
                psus = PSURepository.get_all(session)
                result['psus'] = [p.model_dump() for p in psus]
            
            if component_type in ['all', 'case']:
                cases = CaseRepository.get_all(session)
                result['cases'] = [c.model_dump() for c in cases]
            
            return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Error fetching components: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Camera routes
@app.route('/cameras')
def cameras_page():
    """Camera listings dashboard."""
    return render_template('cameras.html')


@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Get all camera listings."""
    try:
        with get_session() as session:
            active_only = request.args.get('active', 'true').lower() == 'true'
            min_confidence = float(request.args.get('confidence', 0.5))
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            query = """
                SELECT l.*, c.brand as camera_brand, c.model as camera_model, 
                       c.mount, c.sensor, c.camera_type
                FROM listings l
                LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.category = 'camera'
            """
            
            if active_only:
                query += " AND l.is_active = true"
            
            query += " AND l.camera_confidence_score >= :confidence"
            query += " ORDER BY l.date_posted DESC LIMIT :limit OFFSET :offset"
            
            result = session.execute(text(query), {
                'confidence': min_confidence,
                'limit': limit,
                'offset': offset
            })
            
            listings = []
            for row in result.fetchall():
                row_dict = dict(row._mapping)
                listings.append(row_dict)
            
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': listings
            })
    except Exception as e:
        logger.error(f"Error fetching cameras: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/stats', methods=['GET'])
def get_camera_stats():
    """Get camera listings statistics."""
    try:
        with get_session() as session:
            # Total camera listings
            total = session.execute(text("""
                SELECT COUNT(*) FROM listings WHERE category = 'camera'
            """)).scalar()
            
            # Active listings
            active = session.execute(text("""
                SELECT COUNT(*) FROM listings 
                WHERE category = 'camera' AND is_active = true
            """)).scalar()
            
            # Matched listings
            matched = session.execute(text("""
                SELECT COUNT(*) FROM listings 
                WHERE category = 'camera' AND matched_camera_id IS NOT NULL
            """)).scalar()
            
            # Price stats
            price_stats = session.execute(text("""
                SELECT 
                    ROUND(AVG(price_eur), 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price
                FROM listings 
                WHERE category = 'camera' AND is_active = true
            """)).fetchone()
            
            # Brand stats
            brand_stats = session.execute(text("""
                SELECT c.brand, COUNT(*) as count,
                       ROUND(AVG(l.price_eur), 2) as avg_price
                FROM listings l
                JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.category = 'camera' AND l.is_active = true
                GROUP BY c.brand
                ORDER BY count DESC
            """)).fetchall()
            
            # Model stats
            model_stats = session.execute(text("""
                SELECT c.brand, c.model, COUNT(*) as count,
                       ROUND(AVG(l.price_eur), 2) as avg_price,
                       MIN(l.price_eur) as min_price,
                       MAX(l.price_eur) as max_price
                FROM listings l
                JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.category = 'camera' AND l.is_active = true
                GROUP BY c.brand, c.model
                ORDER BY count DESC
                LIMIT 20
            """)).fetchall()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total': total,
                    'active': active,
                    'matched': matched,
                    'avg_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
                    'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
                    'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
                    'brands': [{'brand': b.brand, 'count': b.count, 'avg_price': float(b.avg_price)} for b in brand_stats],
                    'models': [{'brand': m.brand, 'model': m.model, 'count': m.count, 
                               'avg_price': float(m.avg_price), 'min_price': float(m.min_price), 
                               'max_price': float(m.max_price)} for m in model_stats]
                }
            })
    except Exception as e:
        logger.error(f"Error fetching camera stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<listing_id>', methods=['GET'])
def get_camera_detail(listing_id):
    """Get detailed camera listing."""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT l.*, c.*
                FROM listings l
                LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.listing_id = :id AND l.category = 'camera'
            """), {'id': listing_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Listing not found'}), 404
            
            return jsonify({
                'success': True,
                'listing': dict(result._mapping)
            })
    except Exception as e:
        logger.error(f"Error fetching camera detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<listing_id>/flag', methods=['POST'])
def flag_camera(listing_id):
    """Flag a camera listing."""
    try:
        data = request.get_json()
        
        with get_session() as session:
            session.execute(text("""
                INSERT INTO listing_flags (listing_id, flag_type, comment)
                VALUES (:listing_id, :flag_type, :comment)
            """), {
                'listing_id': listing_id,
                'flag_type': data.get('flag_type', 'other'),
                'comment': data.get('comment', '')
            })
            session.commit()
            
            return jsonify({'success': True, 'message': 'Listing flagged successfully'})
    except Exception as e:
        logger.error(f"Error flagging camera: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/flagged', methods=['GET'])
def get_flagged_cameras():
    """Get all flagged camera listings."""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT l.*, c.brand, c.model, lf.flag_type, lf.comment, lf.created_at
                FROM listings l
                JOIN listing_flags lf ON l.listing_id = lf.listing_id
                LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.category = 'camera' AND lf.resolved = false
                ORDER BY lf.created_at DESC
            """))
            
            listings = []
            for row in result.fetchall():
                row_dict = dict(row._mapping)
                listings.append(row_dict)
            
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': listings
            })
    except Exception as e:
        logger.error(f"Error fetching flagged cameras: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/search', methods=['GET'])
def search_cameras():
    """Search camera listings."""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'error': 'Query parameter required'}), 400
        
        with get_session() as session:
            search_pattern = f"%{query}%"
            result = session.execute(text("""
                SELECT l.*, c.brand, c.model
                FROM listings l
                LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
                WHERE l.category = 'camera'
                AND (l.title ILIKE :pattern OR c.brand ILIKE :pattern OR c.model ILIKE :pattern)
                ORDER BY l.date_posted DESC
                LIMIT 100
            """), {'pattern': search_pattern})
            
            listings = []
            for row in result.fetchall():
                row_dict = dict(row._mapping)
                listings.append(row_dict)
            
            return jsonify({
                'success': True,
                'count': len(listings),
                'listings': listings
            })
    except Exception as e:
        logger.error(f"Error searching cameras: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lenses/stats', methods=['GET'])
def get_lens_stats():
    """Get lens price statistics for camera page."""
    try:
        with get_session() as session:
            stats = session.execute(text("""
                SELECT 
                    ROUND(AVG(price_eur), 2) as avg_price,
                    MIN(price_eur) as min_price,
                    MAX(price_eur) as max_price,
                    COUNT(*) as total
                FROM listings 
                WHERE category = 'lens' AND is_active = true
            """)).fetchone()
            
            # Top lens brands
            brand_stats = session.execute(text("""
                SELECT 
                    SPLIT_PART(matched_lens_id, '_', 1) as brand,
                    COUNT(*) as count,
                    ROUND(AVG(price_eur), 2) as avg_price
                FROM listings 
                WHERE category = 'lens' AND is_active = true AND matched_lens_id IS NOT NULL
                GROUP BY SPLIT_PART(matched_lens_id, '_', 1)
                ORDER BY count DESC
                LIMIT 10
            """)).fetchall()
            
            return jsonify({
                'success': True,
                'lens_stats': {
                    'total': stats.total,
                    'avg_price': float(stats.avg_price) if stats.avg_price else 0,
                    'min_price': float(stats.min_price) if stats.min_price else 0,
                    'max_price': float(stats.max_price) if stats.max_price else 0,
                    'brands': [{'brand': b.brand, 'count': b.count, 'avg_price': float(b.avg_price)} for b in brand_stats]
                }
            })
    except Exception as e:
        logger.error(f"Error fetching lens stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Create templates directory if not exists
    templates_dir = os.path.join(project_root, 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create static directory if not exists
    static_dir = os.path.join(project_root, 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    # Create templates
    from web_templates import create_templates
    create_templates(templates_dir)
    
    print("=" * 60)
    print("SS-Crawler Dashboard Server")
    print("=" * 60)
    print(f"Computer listings page: http://localhost:5000/computers")
    print(f"Camera listings page: http://localhost:5000/cameras")
    print(f"API endpoints available at /api/*")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)