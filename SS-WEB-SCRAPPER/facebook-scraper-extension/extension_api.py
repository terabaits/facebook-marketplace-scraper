"""Minimal Flask API for Facebook Scraper Extension."""
import uuid
import re
import os
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database configuration - UPDATE THESE
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'  # <-- UPDATE THIS
}

# Image storage configuration
IMAGE_DIR = Path('G:/Github/SS-WEB-SCRAPPER/images/facebook')
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

def get_db_connection():
    '''Get database connection.'''
    return psycopg2.connect(**DB_CONFIG)


def safe_print(message):
    '''Print safely handling Unicode characters.'''
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # Encode to ASCII, replacing unencodable characters
        if isinstance(message, str):
            safe_msg = message.encode('ascii', 'replace').decode('ascii')
            print(safe_msg, flush=True)
        else:
            print(str(message).encode('ascii', 'replace').decode('ascii'), flush=True)

def download_image(image_url: str, listing_id: str) -> str:
    '''Download image from URL and save locally.
    
    Returns:
        Local path relative to IMAGE_DIR parent, or empty string if failed
        Path format: images/facebook/filename.ext (for Flask /images/ route)
    '''
    if not image_url:
        return ''
    
    try:
        # Determine file extension from URL
        ext = '.jpg'  # default
        if '.png' in image_url.lower():
            ext = '.png'
        elif '.webp' in image_url.lower():
            ext = '.webp'
        elif '.gif' in image_url.lower():
            ext = '.gif'
        
        # Create filename: listing_id_hash.ext
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        filename = f"{listing_id}_{url_hash}{ext}"
        local_path = IMAGE_DIR / filename
        
        # Skip if already exists
        if local_path.exists():
            return f"facebook/{filename}"
        
        # Download image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save image
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        safe_print(f"[DEBUG] Downloaded image: {filename}")
        return f"facebook/{filename}"
        
    except Exception as e:
        safe_print(f"[DEBUG] Failed to download image: {e}")
        return ''

# Enable CORS for extension
CORS(app, resources={
    r"/api/v1/extension/*": {
        "origins": ["chrome-extension://*", "https://www.facebook.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})


@app.route('/api/v1/extension/health', methods=['GET'])
def extension_health():
    '''Health check endpoint for extension.'''
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/v1/extension/analyze', methods=['POST'])
def extension_analyze():
    '''Main endpoint for Chrome extension to analyze listings.'''
    try:
        data = request.get_json()
        
        # Validate required fields
        title = data.get('title', '')
        description = data.get('description', '')
        price = data.get('price', 0)
        currency = data.get('currency', 'EUR')
        
        if not title:
            return jsonify({'success': False, 'error': 'Missing title'}), 400
        
        # Detect components with separate title and description
        detected = detect_components(title, description)
        
        # Fetch prices for detected components
        components = {}
        total_value = 0
        
        for component_type, detection in detected.items():
            matched_id = detection.get('matched_id')
            specs = detection.get('specs') if component_type == 'ram' else None
            prices = get_component_prices(component_type, matched_id, specs)
            components[component_type] = {
                'detected': detection['detected'],
                'normalized': detection['normalized'],
                'matched_model': {
                    'id': matched_id,
                    'name': detection['normalized'],
                    'specifications': detection.get('specs', {})
                },
                'confidence': detection['confidence'],
                'confidence_factors': detection.get('factors', {}),
                'prices': prices
            }
            total_value += prices.get('avg') or 0
        
        # Calculate deal rating
        price_eur = normalize_price(price, currency)
        deal_rating = calculate_deal_rating(price_eur, total_value)
        
        return jsonify({
            'success': True,
            'components': components,
            'pricing': {
                'estimated_total': total_value,
                'listed_price': price_eur,
                'deal_rating': deal_rating['rating'],
                'confidence': deal_rating['confidence']
            },
            'metadata': {
                'processing_time_ms': 0,
                'cache_hit': False,
                'detection_version': '1.0',
                'request_id': str(uuid.uuid4())
            }
        })
        
    except Exception as e:
        import traceback
        print(f'[ERROR] Analysis failed: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def detect_components(title, description):
    '''Detect PC components from text with logic to handle individual component listings.
    
    Key logic:
    - GPU detection: Only if title contains GPU keywords (title is primary for GPU)
    - CPU/RAM/SSD detection: Only if listing appears to be a full computer
    - A listing is considered "full PC" if it has multiple component keywords in description
      OR if title suggests a full system (pc, computer, gaming, desktop, etc.)
    '''
    try:
        safe_title = title[:50].encode('ascii', 'replace').decode('ascii')
        safe_print(f"[DEBUG] detect_components called with title: '{safe_title}...'")
    except:
        safe_print(f"[DEBUG] detect_components called with title: [Unicode title]...")
    
    components = {}
    
    if not title:
        print("[DEBUG] No title provided, returning empty", flush=True)
        return components
    
    title_lower = title.lower()
    desc_lower = description.lower() if description else ''
    
    # Check if title contains GPU keywords (for GPU detection)
    title_gpu_keywords = re.search(r'\b(gtx|rtx|rx\s*\d+|geforce|radeon)\b', title_lower)
    
    # Also check for standalone GPU model numbers (e.g., "1080TI", "1080 ti", "9070 XT")
    title_gpu_model = re.search(r'\b(10|16|20|30|40|90)\d{2,3}\s*(ti|xt|gre|super)?\b', title_lower)
    
    # Check if title suggests a full PC listing
    pc_keywords = r'\b(pc|computer|gaming|desktop|tower|system|build|setup|complete)\b'
    title_suggests_pc = re.search(pc_keywords, title_lower)
    
    # Check description for multiple component types (indicates full PC listing)
    desc_has_gpu = bool(re.search(r'\b(gtx|rtx|rx\d+|geforce|radeon|\d{4}\s*ti)\b', desc_lower))
    desc_has_cpu = bool(re.search(r'\b(ryzen|intel\s+core|i[3579]|pentium|celeron)\b', desc_lower))
    desc_has_ram = bool(re.search(r'\b(\d{1,3})\s?gb\s+(ddr|ram)\b', desc_lower))
    desc_has_storage = bool(re.search(r'\b(ssd|hdd|nvme|m\.2|\d{3,4}gb\s+storage)\b', desc_lower))
    
    # Count component types in description
    component_count = sum([desc_has_gpu, desc_has_cpu, desc_has_ram, desc_has_storage])
    desc_suggests_pc = component_count >= 3  # 3+ different component types = likely a PC
    
    # Determine if this is a full PC listing
    is_full_pc = title_suggests_pc or desc_suggests_pc
    
    safe_print(f"[DEBUG] title_suggests_pc: {bool(title_suggests_pc)}, desc_suggests_pc: {desc_suggests_pc} (count={component_count}), is_full_pc: {is_full_pc}")
    safe_print(f"[DEBUG] desc_has_gpu: {desc_has_gpu}, desc_has_cpu: {desc_has_cpu}, desc_has_ram: {desc_has_ram}, desc_has_storage: {desc_has_storage}")
    
    # GPU Detection: Only if title contains GPU keywords OR GPU model number
    if title_gpu_keywords or title_gpu_model:
        # Use title for GPU detection, description only for confirmation
        search_text = title
        if description:
            # Check if description confirms this is about a GPU (not conflicting)
            search_text = f"{title} {description}"
        
        gpu_match = detect_gpu(search_text)
        if gpu_match:
            # Additional check: GPU should be in title or description should confirm it's the main item
            # A GPU is confirmed if:
            # 1. Title contains GPU model name, OR
            # 2. Description mentions GPU prominently (e.g., "selling my GPU", "graphics card for sale")
            
            # Check if title starts with or prominently features GPU model
            gpu_in_title = bool(re.search(r'\b(gtx|rtx|rx\s*\d|geforce|radeon|\d{4}\s*(ti|xt|gre))', title_lower.strip()))
            
            # Check if description confirms GPU is being sold (not just mentioned as part of PC specs)
            gpu_sale_terms = r'\b(graphics\s+card|gpu|video\s+card|vga)\b'
            desc_confirms_gpu = bool(re.search(gpu_sale_terms, desc_lower))
            
            # If title starts with GPU model, it's likely a GPU-only listing
            if gpu_in_title or desc_confirms_gpu or not is_full_pc:
                components['gpu'] = gpu_match
    
    # CPU/RAM/SSD Detection: For full PC listings OR component-specific listings
    # Check if title suggests a specific component listing
    ram_keywords = r'\b(ram|memory|ddr[345]|kingston|corsair|gskill)\b'
    ssd_keywords = r'\b(ssd|hdd|nvme|m\.2|samsung\s+ssd|crucial\s+ssd)\b'
    cpu_keywords = r'\b(cpu|processor|ryzen|intel\s+core|i[3579]-)\b'
    
    is_ram_listing = bool(re.search(ram_keywords, title_lower))
    is_ssd_listing = bool(re.search(ssd_keywords, title_lower))
    is_cpu_listing = bool(re.search(cpu_keywords, title_lower))
    
    safe_print(f"[DEBUG] Component listings: ram={is_ram_listing}, ssd={is_ssd_listing}, cpu={is_cpu_listing}")
    
    # CPU detection
    if is_full_pc or is_cpu_listing:
        cpu_match = detect_cpu(f"{title} {description}")
        if cpu_match:
            components['cpu'] = cpu_match
            safe_print(f"[DEBUG] CPU detected: {cpu_match}")
        elif is_cpu_listing:
            print("[DEBUG] CPU: Title suggests CPU but no match found", flush=True)
    
    # RAM detection
    if is_full_pc or is_ram_listing:
        ram_match = detect_ram(f"{title} {description}")
        if ram_match:
            components['ram'] = ram_match
            safe_print(f"[DEBUG] RAM detected: {ram_match}")
        elif is_ram_listing:
            print("[DEBUG] RAM: Title suggests RAM but no match found", flush=True)
    
    # SSD detection
    if is_full_pc or is_ssd_listing:
        ssd_match = detect_ssd(f"{title} {description}")
        if ssd_match:
            components['ssd'] = ssd_match
            safe_print(f"[DEBUG] SSD detected: {ssd_match}")
        elif is_ssd_listing:
            print("[DEBUG] SSD: Title suggests SSD but no match found", flush=True)
    
    safe_print(f"[DEBUG] detect_components returning: {list(components.keys())}")
    return components


def detect_gpu(text):
    '''Detect GPU model from text and match to database.'''
    safe_print(f"[DEBUG] detect_gpu called with text length: {len(text)}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        patterns = [
            (r'\brtx\s*(20|30|40)(60|70|80|90)\s*(ti|super)?\b', 'nvidia'),
            (r'\brx\s?(5|6|7|8|9)\d{2,4}\s?(xt|gre)?\b', 'amd'),  # RX580, RX 580, RX 580 XT, RX 9070 XT
            (r'\bgtx\s*(10|16)?(\d{3,4})\s*(ti)?\b', 'nvidia'),  # GTX 1080, GTX 1660, GTX 960
            (r'\b(10|16)(\d{2,3})(ti)?\b', 'nvidia'),  # 1080ti, 1660ti, 960
            (r'\b(\d{3,4})\s*(ti|super)?\b', 'nvidia'),  # 1080, 1080 ti, 1080ti, 960, 970
            (r'\b(\d{3,4})(TI|ti|Ti)\b', 'nvidia')  # 1080TI, 960TI (no space)
        ]
        
        text_lower = text.lower()
        safe_print(f"[DEBUG] Searching in text: {text_lower[:200]}...")
        
        for pattern, brand in patterns:
            match = re.search(pattern, text_lower)
            if match:
                detected = match.group(0).strip()
                safe_print(f"[DEBUG] Pattern matched: '{detected}' with pattern: {pattern}")
                normalized = normalize_gpu_model(detected)
                
                safe_print(f"[DEBUG] detect_gpu: detected='{detected}', normalized='{normalized}'")
                
                # Query database for actual GPU match
                # IMPORTANT: For non-Ti/Super searches, immediately exclude Ti/Super variants
                # to prevent matching RTX 3070 Ti when the listing only says RTX 3070
                search_pattern = f"%{normalized}%"
                if 'ti' not in detected.lower() and 'super' not in detected.lower():
                    cursor.execute("""
                        SELECT id, model FROM gpu_reference 
                        WHERE model ILIKE %s
                        AND model NOT ILIKE '%%ti%%'
                        AND model NOT ILIKE '%%super%%'
                        LIMIT 1
                    """, (search_pattern,))
                else:
                    # For Ti/Super searches, include them
                    cursor.execute("""
                        SELECT id, model FROM gpu_reference 
                        WHERE model ILIKE %s
                        LIMIT 1
                    """, (search_pattern,))
                result = cursor.fetchone()
                safe_print(f"[DEBUG] Query result: {result}")
                
                matched_id = result[0] if result else None
                db_model = result[1] if result else normalized
                
                return {
                    'detected': detected,
                    'normalized': db_model if result else normalized,
                    'matched_id': matched_id,
                    'confidence': 0.9 if result else 0.75,
                    'factors': {
                        'pattern_match': 0.9, 
                        'db_match': 0.95 if result else 0.5,
                        'context_bonus': 0.8
                    }
                }
        
        print("[DEBUG] No GPU pattern matched", flush=True)
        return None
    finally:
        cursor.close()
        conn.close()


def normalize_gpu_model(detected):
    '''Normalize GPU model name.'''
    detected_lower = detected.lower()
    detected_nospace = detected_lower.replace(' ', '')
    
    # Check for RTX first
    if 'rtx' in detected_nospace:
        series = re.search(r'(20|30|40)(60|70|80|90)', detected_nospace)
        if series:
            series_num = series.group(1)
            tier = series.group(2)
            suffix = ''
            if 'ti' in detected_nospace:
                suffix = ' ti'
            elif 'super' in detected_nospace:
                suffix = ' super'
            return f'geforce rtx {series_num}{tier}{suffix}'
    
    # Check for RX (AMD)
    if 'rx' in detected_nospace:
        # Match: rx580, rx 580, rx5700, rx 6700 xt, rx 9070, rx 9070 xt
        match = re.search(r'rx(5|6|7|8|9)(\d{2,4})', detected_nospace)
        if match:
            series = match.group(1)
            model = match.group(2)
            suffix = ''
            if 'xt' in detected_nospace:
                suffix = ' xt'
            elif 'gre' in detected_nospace:
                suffix = ' gre'
            return f'amd radeon rx{series}{model}{suffix}'
    
    # Check for GTX or just model number (e.g., "1080ti", "960")
    # Pattern: optional gtx prefix + optional series + model + optional ti
    # (gtx)? makes GTX optional, (10|16|9)? makes series optional, \d{3,4} matches 960/1080/1660/etc
    match = re.search(r'(gtx)?(10|16|9)?(\d{3,4})(ti)?', detected_nospace)
    safe_print(f"[DEBUG] GTX regex match: {match}, groups: {match.groups() if match else None}")
    if match and match.group(3):  # Must have model number (group 3)
        has_gtx = match.group(1) is not None
        series = match.group(2)  # Series like '10', '16', or '9', may be None
        model = match.group(3)   # 3-4 digit model like '960', '1080' or '1660'
        suffix = ' ti' if (match.group(4) or detected_nospace.endswith('ti')) else ''
        
        # Handle 3-digit models (like 960, 970, 980) vs 4-digit models (1080, 1660)
        if len(model) == 3:
            # 3-digit models (960, 970, 980) - already in full form
            result = f'geforce gtx {model}{suffix}'
        elif series:
            # If series was specified separately (gtx 1080), use it
            result = f'geforce gtx {series}{model}{suffix}'
        else:
            # If just "1080ti" - model already has series prefix
            result = f'geforce gtx {model}{suffix}'
        
        safe_print(f"[DEBUG] has_gtx={has_gtx}, series='{series}', model='{model}', suffix='{suffix}'")
        safe_print(f"[DEBUG] GTX result: '{result}'")
        return result
    
    # Fallback: just return as-is
    return detected_lower


def detect_cpu(text):
    '''Detect CPU model from text and match to database.'''
    safe_print(f"[DEBUG] detect_cpu called with text length: {len(text)}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        patterns = [
            r'\b(i[3579])[-\s]?(\d{3,5})([kft]?)\b',
            r'\b(ryzen|r)\s*(3|5|7|9)?\s+(\d{3,4})(x3d|x3D|X3D|[xg]?)\b',
            r'\b(ryzen)\s+(\d{4,5})(x3d|x3D|X3D|[xg]?)\b'  # Match "Ryzen 5500X3D" without tier
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                detected = match.group(0).strip()
                normalized = normalize_cpu_model(detected)
                safe_print(f"[DEBUG] CPU detected: '{detected}', normalized: '{normalized}'")
                
                # Query database for actual CPU match
                cursor.execute('''
                    SELECT id, processor_number FROM cpu_reference 
                    WHERE processor_number ILIKE %s OR processor_number ILIKE %s
                    ORDER BY 
                        CASE WHEN processor_number ILIKE %s THEN 1 ELSE 2 END,
                        LENGTH(processor_number) DESC
                    LIMIT 1
                ''', (f"%{normalized}%", f"%{detected}%", f"%{normalized}%"))
                result = cursor.fetchone()
                
                matched_id = result[0] if result else None
                db_model = result[1] if result else normalized
                
                confidence = 0.85 if result else 0.7
                safe_print(f"[DEBUG] CPU result: matched_id={matched_id}, confidence={confidence}")
                
                return {
                    'detected': detected,
                    'normalized': db_model if result else normalized,
                    'matched_id': matched_id,
                    'confidence': confidence,
                    'factors': {
                        'pattern_match': 0.85, 
                        'db_match': 0.9 if result else 0.5,
                        'context_bonus': 0.75
                    }
                }
        
        print("[DEBUG] CPU: No pattern matched", flush=True)
        return None
    finally:
        cursor.close()
        conn.close()


def normalize_cpu_model(detected):
    '''Normalize CPU model name.'''
    detected = detected.lower()
    
    # Intel
    intel_match = re.search(r'i([3579])[-\s]?(\d{3,5})([kft]?)', detected)
    if intel_match:
        tier = intel_match.group(1)
        model = intel_match.group(2)
        suffix = intel_match.group(3).upper() if intel_match.group(3) else ''
        return f'intel core i{tier}-{model}{suffix}'
    
    # AMD - try pattern with tier first
    amd_match = re.search(r'ryzen\s*(3|5|7|9)\s+(\d{3,4})(x3d|x3D|X3D|[xg]?)', detected)
    if amd_match:
        tier = amd_match.group(1)
        model = amd_match.group(2)
        suffix = amd_match.group(3).upper() if amd_match.group(3) else ''
        # Handle X3D specifically
        if 'X3D' in suffix or 'x3d' in suffix or 'x3D' in suffix:
            suffix = 'X3D'
        return f'amd ryzen {tier} {model}{suffix}'
    
    # AMD - pattern without explicit tier (e.g., "Ryzen 5500X3D")
    # Infer tier from first digit of model: 3->3, 5->5, 7->7, 9->9
    amd_match_no_tier = re.search(r'ryzen\s+(\d)(\d{3,4})(x3d|x3D|X3D|[xg]?)', detected)
    if amd_match_no_tier:
        tier = amd_match_no_tier.group(1)
        model = amd_match_no_tier.group(1) + amd_match_no_tier.group(2)  # Full model number
        suffix = amd_match_no_tier.group(3).upper() if amd_match_no_tier.group(3) else ''
        if 'X3D' in suffix or 'x3d' in suffix or 'x3D' in suffix:
            suffix = 'X3D'
        return f'amd ryzen {tier} {model}{suffix}'
    
    return detected


def detect_ram(text):
    '''Detect RAM configuration from text and match to database.'''
    safe_print(f"[DEBUG] detect_ram called with text length: {len(text)}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        text_lower = text.lower()
        detected = None
        capacity = None
        ddr_type = None
        speed_mhz = None
        
        # Pattern 1: "32GB DDR4" or "16GB DDR5"
        match1 = re.search(r'\b(\d{1,3})\s?gb?\s+(ddr[345])\b', text_lower)
        if match1:
            capacity = match1.group(1)
            ddr_type = match1.group(2).upper()
            detected = f'{capacity}GB {ddr_type}'
            safe_print(f"[DEBUG] RAM pattern 1 matched: '{match1.group(0)}' -> {detected}")
        
        # Pattern 2: "DDR4-3200" or "DDR5 5600"
        if not detected:
            match2 = re.search(r'\b(ddr[345])[-\s]?(\d{3,5})\b', text_lower)
            if match2:
                ddr_type = match2.group(1).upper()
                speed_mhz = match2.group(2)
                # Try to find capacity nearby
                cap_match = re.search(r'(\d{1,3})\s?gb', text_lower)
                if cap_match:
                    capacity = cap_match.group(1)
                    detected = f'{capacity}GB {ddr_type}'
                    safe_print(f"[DEBUG] RAM pattern 2 matched: '{match2.group(0)}' -> {detected}")
        
        # Pattern 3 & 4: "32GB RAM" or "RAM 32GB" - need to infer DDR type from speed
        if not detected:
            match3 = re.search(r'\b(\d{1,3})\s?gb?\s+ram\b', text_lower)
            match4 = re.search(r'\bram\s+(\d{1,3})\s?gb?\b', text_lower)
            
            if match3 or match4:
                capacity = (match3 or match4).group(1)
                safe_print(f"[DEBUG] RAM capacity found: {capacity}GB")
                
                # Look for speed to determine DDR type
                # DDR3: 800-2133 MHz
                # DDR4: 2133-3200 MHz  
                # DDR5: 4800-6400+ MHz
                speed_match = re.search(r'(\d{4,5})\s?(mhz|mt/s|mt/s)', text_lower)
                if speed_match:
                    speed_val = int(speed_match.group(1))
                    speed_mhz = speed_match.group(1)
                    if speed_val >= 4800:
                        ddr_type = 'DDR5'
                    elif speed_val >= 2133:
                        ddr_type = 'DDR4'
                    else:
                        ddr_type = 'DDR3'
                    safe_print(f"[DEBUG] RAM speed {speed_val} -> inferred {ddr_type}")
                else:
                    # Default to DDR4 if no speed found
                    ddr_type = 'DDR4'
                    safe_print(f"[DEBUG] RAM no speed found, defaulting to DDR4")
                
                detected = f'{capacity}GB {ddr_type}'
                safe_print(f"[DEBUG] RAM detected via pattern 3/4: '{detected}'")
        
        if not detected:
            print("[DEBUG] RAM: No pattern matched", flush=True)
            return None
        
        # Query database for matching RAM
        cursor.execute('''
            SELECT id, name, capacity_gb, type, speed, modules 
            FROM ram_reference 
            WHERE capacity_gb = %s::int 
            AND type ILIKE %s
            ORDER BY rating DESC NULLS LAST
            LIMIT 1
        ''', (capacity, f'%{ddr_type}%'))
        
        result = cursor.fetchone()
        
        if result:
            safe_print(f"[DEBUG] RAM matched to DB: {result[1]} (ID: {result[0]})")
            return {
                'detected': detected,
                'normalized': result[1],  # name
                'matched_id': result[0],   # id
                'specs': {
                    'capacity_gb': result[2],
                    'type': result[3],
                    'speed': result[4],
                    'modules': result[5]
                },
                'confidence': 0.85 if result else 0.6,
                'factors': {
                    'pattern_match': 0.85, 
                    'db_match': 0.9 if result else 0.5,
                    'context_bonus': 0.75
                }
            }
        
        # Fallback if no DB match
        return {
            'detected': detected,
            'normalized': detected.lower(),
            'matched_id': None,
            'confidence': 0.6,
            'factors': {'pattern_match': 0.7, 'context_bonus': 0.5}
        }
        
    finally:
        cursor.close()
        conn.close()


def detect_ssd(text):
    '''Detect SSD from text.'''
    pattern = r'\b(\d{3,4})\s?gb?\s+(ssd|nvme|m\.2)\b'
    match = re.search(pattern, text.lower())
    
    if match:
        capacity = match.group(1)
        interface = match.group(2).upper()
        detected = f'{capacity}GB {interface}'
        
        return {
            'detected': detected,
            'normalized': detected.lower(),
            'matched_id': f'ssd_{hash(detected) % 100000}',
            'confidence': 0.7,
            'factors': {'pattern_match': 0.75, 'context_bonus': 0.65}
        }
    
    return None


def get_component_prices(component_type, component_id, component_specs=None):
    '''Fetch price data for a component from actual sold listings.'''
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Map component type to database column
        column_map = {
            'gpu': 'matched_gpu_id',
            'cpu': 'matched_cpu_id',
            'ram': 'matched_ram_id'
        }
        
        if component_type not in column_map:
            return {
                'avg': None,
                'min': None,
                'max': None,
                'currency': 'EUR',
                'sample_size': 0,
                'source': 'unknown'
            }
        
        column = column_map[component_type]
        results = []
        
        # If we have a matched_id, query by that first
        if component_id:
            cursor.execute(f'''
                SELECT price_eur
                FROM listings 
                WHERE {column} = %s 
                AND price_eur > 0 
                AND price_eur < 10000
                ORDER BY created_at DESC
                LIMIT 50
            ''', (component_id,))
            results = cursor.fetchall()
            safe_print(f"[DEBUG] Query by {column}={component_id}: {len(results)} results")
        
        # If no results and it's RAM, try fallback by specs
        if len(results) == 0 and component_type == 'ram' and component_specs:
            capacity = component_specs.get('capacity_gb')
            ddr_type = component_specs.get('type')
            
            if capacity and ddr_type:
                safe_print(f"[DEBUG] Fallback: Looking up RAM prices by specs: {capacity}GB {ddr_type}")
                cursor.execute('''
                    SELECT l.price_eur
                    FROM listings l
                    JOIN ram_reference r ON l.matched_ram_id = r.id
                    WHERE l.category = 'ram'
                    AND l.price_eur > 0 
                    AND l.price_eur < 10000
                    AND r.capacity_gb = %s
                    AND r.type ILIKE %s
                    ORDER BY l.created_at DESC
                    LIMIT 50
                ''', (capacity, f'%{ddr_type}%'))
                results = cursor.fetchall()
                safe_print(f"[DEBUG] Fallback query: {len(results)} results")
        
        if results:
            prices = [float(r[0]) for r in results]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            return {
                'avg': round(avg_price, 2),
                'min': round(min_price, 2),
                'max': round(max_price, 2),
                'currency': 'EUR',
                'sample_size': len(prices),
                'source': 'database'
            }
        
        safe_print(f"[DEBUG] No price data found")
        return {
            'avg': None,
            'min': None,
            'max': None,
            'currency': 'EUR',
            'sample_size': 0,
            'source': 'unknown'
        }
        
    except Exception as e:
        # Return unknown on error
        return {
            'avg': None,
            'min': None,
            'max': None,
            'currency': 'EUR',
            'sample_size': 0,
            'source': 'error'
        }
        
    finally:
        cursor.close()
        conn.close()


def normalize_price(price, currency):
    '''Normalize price to EUR.'''
    rates = {'EUR': 1.0, 'USD': 0.92, 'GBP': 1.17}
    return price * rates.get(currency, 1.0)


def calculate_deal_rating(listed_price, estimated_value):
    '''Calculate deal rating.'''
    if not estimated_value or estimated_value == 0:
        return {'rating': 'unknown', 'confidence': 0}
    
    # Convert Decimal to float if needed
    if hasattr(estimated_value, 'quantize'):  # Check if it's a Decimal
        estimated_value = float(estimated_value)
    
    ratio = listed_price / estimated_value
    
    if ratio <= 0.6:
        rating = 'excellent'
    elif ratio <= 0.8:
        rating = 'good'
    elif ratio <= 1.0:
        rating = 'fair'
    elif ratio <= 1.2:
        rating = 'high'
    else:
        rating = 'overpriced'
    
    return {'rating': rating, 'ratio': round(ratio, 2), 'confidence': 0.8}


@app.route('/api/v1/extension/import', methods=['POST'])
def import_listing():
    '''Import a Facebook Marketplace listing to the database.'''
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        data = request.get_json()
        
        # Required fields
        title = data.get('title', '')
        description = data.get('description', '')
        price = data.get('price', 0)
        currency = data.get('currency', 'EUR')
        listing_url = data.get('listing_url', '')
        image_url = data.get('image_url', '')
        seller_location = data.get('seller_location', 'Unknown')
        components = data.get('components', {})
        
        if not title or not price:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Normalize price to EUR
        price_eur = normalize_price(price, currency)
        
        # Get component IDs if matched
        matched_gpu_id = None
        matched_cpu_id = None
        matched_ram_id = None
        matched_ssd_id = None
        
        if 'gpu' in components:
            matched_gpu_id = components['gpu'].get('matched_id') or components['gpu'].get('matched_model', {}).get('id')
        
        if 'cpu' in components:
            matched_cpu_id = components['cpu'].get('matched_id') or components['cpu'].get('matched_model', {}).get('id')
        
        if 'ram' in components:
            matched_ram_id = components['ram'].get('matched_id') or components['ram'].get('matched_model', {}).get('id')
        
        # Generate unique listing ID from URL
        import hashlib
        import time
        url_hash = hashlib.md5(listing_url.encode()).hexdigest()[:16] if listing_url else str(int(time.time()))
        listing_id = f"fb_{url_hash}"
        
        # Generate content hash for duplicate detection
        content_fingerprint = f"{title}:{description}:{price_eur}:{seller_location}"
        content_hash = hashlib.md5(content_fingerprint.encode()).hexdigest()
        
        # Determine category based on detected components
        detected_types = []
        if 'gpu' in components:
            detected_types.append('gpu')
        if 'cpu' in components:
            detected_types.append('cpu')
        if 'ram' in components:
            detected_types.append('ram')
        if 'ssd' in components:
            detected_types.append('ssd')
        
        if len(detected_types) == 1:
            # Single component listing
            category = detected_types[0]
        elif len(detected_types) > 1:
            # Multiple components = full PC
            category = 'computer'
        else:
            # No components detected, check data or default to computer
            category = data.get('category', 'computer')
        
        safe_print(f"[DEBUG] Detected components: {detected_types}, using category: {category}")
        
        # Download image locally
        local_image_path = download_image(image_url, listing_id)
        
        # Check if source column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'listings' AND column_name = 'source'
        """)
        has_source_col = cursor.fetchone() is not None
        
        if has_source_col:
            # Insert with source and content_hash and local_image_path
            cursor.execute('''
                INSERT INTO listings 
                (listing_id, category, title, description, price_eur,
                 listing_url, image_url, seller_location, date_posted, is_active,
                 matched_gpu_id, matched_cpu_id, matched_ram_id, confidence_score, match_method, source, content_hash, local_image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), true, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (listing_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price_eur = EXCLUDED.price_eur,
                    is_active = true,
                    updated_at = NOW()
                RETURNING listing_id
            ''', (
                listing_id,
                category,
                title,
                description,
                price_eur,
                listing_url,
                image_url,
                seller_location,
                matched_gpu_id,
                matched_cpu_id,
                matched_ram_id,
                0.8 if components else 0.5,
                'extension_import' if components else 'manual',
                'facebook_extension' if components else 'facebook_manual',
                content_hash,
                local_image_path
            ))
        else:
            # Insert without source but with content_hash and local_image_path
            cursor.execute('''
                INSERT INTO listings 
                (listing_id, category, title, description, price_eur,
                 listing_url, image_url, seller_location, date_posted, is_active,
                 matched_gpu_id, matched_cpu_id, matched_ram_id, confidence_score, match_method, content_hash, local_image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), true, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (listing_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price_eur = EXCLUDED.price_eur,
                    is_active = true,
                    updated_at = NOW()
                RETURNING listing_id
            ''', (
                listing_id,
                category,
                title,
                description,
                price_eur,
                listing_url,
                image_url,
                seller_location,
                matched_gpu_id,
                matched_cpu_id,
                matched_ram_id,
                0.8 if components else 0.5,
                'extension_import' if components else 'manual',
                content_hash,
                local_image_path
            ))
        
        listing_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({
            'success': True,
            'listing_id': listing_id,
            'message': 'Listing imported successfully'
        })
        
    except Exception as e:
        conn.rollback()
        import traceback
        print(f'[ERROR] Import failed: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print('Starting Extension API Server...')
    print('Health: http://localhost:5001/api/v1/extension/health')
    print('Analyze: http://localhost:5001/api/v1/extension/analyze')
    app.run(host='0.0.0.0', port=5001, debug=True)
