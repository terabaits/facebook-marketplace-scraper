import re

with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the RAM query section
old_pattern = r'''# Simplified query - just get all 8GB listings and manually filter
                    # DEBUG: Get list of listings used for calculation
                    debug_query = """
                        SELECT l.listing_id, l.title, l.price_eur, l.is_active, 
                               r.name as ram_name, r.capacity_gb as ref_capacity
                        FROM listings l
                        LEFT JOIN ram_reference r ON l.matched_ram_id = r.id
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ram' 
                            AND fl.listing_id IS NULL
                            AND (
                                -- Matched RAM with capacity in reference
                                \(l.matched_ram_id IS NOT NULL AND r.capacity_gb = %s\)
                                -- OR unmatched with capacity in title
                                OR \(l.matched_ram_id IS NULL AND l.title ILIKE %s\)
                            \)
                        ORDER BY l.price_eur
                    """
                    
                    generic_ram_query = """
                        SELECT ROUND\(AVG\(l.price_eur\)::numeric, 2\) as avg_price,
                               MIN\(l.price_eur\) as min_price,
                               MAX\(l.price_eur\) as max_price,
                               COUNT\(\*\) as listing_count
                        FROM listings l
                        LEFT JOIN ram_reference r ON l.matched_ram_id = r.id
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ram' 
                            AND fl.listing_id IS NULL
                            AND (
                                -- Matched RAM with capacity in reference
                                \(l.matched_ram_id IS NOT NULL AND r.capacity_gb = %s\)
                                -- OR unmatched with capacity in title
                                OR \(l.matched_ram_id IS NULL AND l.title ILIKE %s\)
                            \)
                    """'''

new_code = '''# Query by capacity and DDR type using r.type column
                    # DEBUG: Get list of listings used for calculation
                    debug_query = """
                        SELECT l.listing_id, l.title, l.price_eur, l.is_active, 
                               r.name as ram_name, r.capacity_gb as ref_capacity, r.type as ddr_type
                        FROM listings l
                        LEFT JOIN ram_reference r ON l.matched_ram_id = r.id
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ram' 
                            AND fl.listing_id IS NULL
                            AND (
                                -- Matched RAM with capacity and DDR type
                                (l.matched_ram_id IS NOT NULL AND r.capacity_gb = %s AND r.type = %s)
                                -- OR unmatched with capacity in title
                                OR (l.matched_ram_id IS NULL AND l.title ILIKE %s)
                            )
                        ORDER BY l.price_eur
                    """
                    
                    generic_ram_query = """
                        SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
                               MIN(l.price_eur) as min_price,
                               MAX(l.price_eur) as max_price,
                               COUNT(*) as listing_count
                        FROM listings l
                        LEFT JOIN ram_reference r ON l.matched_ram_id = r.id
                        LEFT JOIN flagged_listings fl ON l.listing_id = fl.listing_id
                        WHERE l.category = 'ram' 
                            AND fl.listing_id IS NULL
                            AND (
                                -- Matched RAM with capacity and DDR type
                                (l.matched_ram_id IS NOT NULL AND r.capacity_gb = %s AND r.type = %s)
                                -- OR unmatched with capacity in title
                                OR (l.matched_ram_id IS NULL AND l.title ILIKE %s)
                            )
                    """
                    
                    title_capacity_pattern = f"%{ram_capacity}GB%"
                    ddr_type = ram_type or 'DDR4'  # e.g., 'DDR4', 'DDR3'
                    
                    # Debug: print all matching listings
                    cursor.execute(debug_query, (ram_capacity, ddr_type, title_capacity_pattern))
                    all_listings = cursor.fetchall()
                    print(f"DEBUG RAM: Found {len(all_listings)} total {ram_capacity}GB {ddr_type} listings")
                    ddr4_count = sum(1 for dl in all_listings if dl.get('ddr_type') == 'DDR4')
                    ddr3_count = sum(1 for dl in all_listings if dl.get('ddr_type') == 'DDR3')
                    unmatched_count = len(all_listings) - ddr4_count - ddr3_count
                    print(f"  DDR4: {ddr4_count}, DDR3: {ddr3_count}, Unmatched: {unmatched_count}")
                    for dl in all_listings[:15]:
                        ram_info = dl.get('ram_name') or 'unmatched'
                        ddr_info = dl.get('ddr_type') or 'unmatched'
                        print(f"  - {dl['listing_id']}: €{dl['price_eur']} - {ddr_info} - {ram_info[:40]}")
                    if len(all_listings) > 15:
                        print(f"  ... and {len(all_listings) - 15} more")
                    
                    cursor.execute(generic_ram_query, (ram_capacity, ddr_type, title_capacity_pattern))'''

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_code, content)
    print('Replaced RAM query with DDR type filtering')
    with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print('Pattern not found, trying simpler replacement...')
    # Try a simpler approach
    content = content.replace(
        'cursor.execute(generic_ram_query, (ram_capacity, title_capacity_pattern))',
        '''title_capacity_pattern = f"%{ram_capacity}GB%"
                    ddr_type = ram_type or 'DDR4'
                    
                    # Execute query with DDR type filter
                    cursor.execute(generic_ram_query, (ram_capacity, ddr_type, title_capacity_pattern))'''
    )
    with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Applied simpler replacement')
