import sys

# Read the file
with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/app.py', 'r') as f:
    content = f.read()

# Find and replace the price stats query
old_query = '''        # Get price stats for each DDR type and capacity
        cursor.execute("""
            SELECT 
                r.type,
                r.capacity_gb,
                COUNT(*) as listing_count,
                AVG(l.price_eur) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price
            FROM listings l
            JOIN ram_reference r ON l.matched_ram_id = r.id
            WHERE l.category = 'ram' AND l.is_active = true
            GROUP BY r.type, r.capacity_gb
        """)'''

new_query = '''        # Build price stats query with same filters as listings query
        stats_params = []
        stats_where = "WHERE l.category = 'ram' AND l.is_active = true"
        
        if capacity_filter:
            stats_where += " AND r.capacity_gb = %s"
            stats_params.append(int(capacity_filter))
        if type_filter:
            stats_where += " AND r.type ILIKE %s"
            stats_params.append(f'%{type_filter}%')
        
        stats_query = f"""
            SELECT 
                r.type,
                r.capacity_gb,
                COUNT(*) as listing_count,
                AVG(l.price_eur) as avg_price,
                MIN(l.price_eur) as min_price,
                MAX(l.price_eur) as max_price
            FROM listings l
            JOIN ram_reference r ON l.matched_ram_id = r.id
            {stats_where}
            GROUP BY r.type, r.capacity_gb
        """
        
        cursor.execute(stats_query, stats_params)'''

if old_query in content:
    content = content.replace(old_query, new_query)
    with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/app.py', 'w') as f:
        f.write(content)
    print("Successfully updated price stats query")
else:
    print("Could not find the query to replace")
    sys.exit(1)
