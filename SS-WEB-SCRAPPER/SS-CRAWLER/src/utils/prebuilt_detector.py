"""Prebuilt and mini PC detection keywords database."""

# NOTE: We intentionally do NOT include broad OEM brand names like
# "DELL", "HP", "LENOVO" as standalone prebuilt signals. Those words
# appear all the time in custom-build listings (e.g. a "DELL 240W
# SSD" or "HP Pavilion Laptop"). The prebuilt flag should fire on
# specific prebuilt MODEL SERIES (Optiplex, ProDesk, ThinkCentre,
# ...) or strong prebuilt brand names (Alienware, NZXT, ...), not on
# any OEM mention.
PREBUILT_BRANDS = {
    # Gaming prebuilts — strong signals (these names essentially
    # only appear in prebuilt contexts)
    'ALIENWARE', 'AURORA', 'PREDATOR', 'OMEN', 'LEGION', 'ROG', 'TUF',
    'IBUYPOWER', 'CORSAIR', 'ORIGIN PC', 'NZXT', 'CYBERPOWERPC',
    'FALCON NORTHWEST', 'MAINGEAR', 'DIGITAL STORM',

    # Mini PCs (NUC, Beelink, etc. are prebuilt by definition)
    'INTEL NUC', 'ASUS PN', 'MINIS FORUM', 'BEELINK', 'GEEKOM',
    'CHUWI', 'MOREFINE', 'AOOSTAR', 'GMKTEC', 'ACEMAGIC',

    # Common prebuilt model series — these are the real "is this a
    # prebuilt" signal per user request: listings that mention Optiplex,
    # ProDesk, ThinkCentre, etc. are prebuilts by definition.
    'OPTIPLEX', 'PRECISION', 'ELITEDESK', 'PRODESK', 'THINKCENTRE',
    'THINKSTATION', 'THINKPAD', 'VOSTRO', 'INSPIRON', 'XPS',
    'PAVILION', 'ENVY', 'SPECTRE', 'OMEN BY HP',
    'SATELLITE', 'ASPIRE', 'VERITON', 'IDEACENTRE', 'IDEAPAD',
    'SURFACE', 'STUDIO XPS', 'GAMING DESKTOP',

    # All-in-One (always prebuilt)
    'IMAC', 'ALL-IN-ONE', 'AIO', 'ALL IN ONE',
    'MAC MINI', 'MAC STUDIO',
}

# Keywords that indicate prebuilt/mini PCs
PREBUILT_KEYWORDS = [
    # Form factor indicators
    'PREBUILT', 'PRE-BUILT', 'PRE BUILT',
    'BRAND PC', 'FACTORY PC', 'OEM PC',
    'MINI PC', 'MINIPC', 'NUC', 'COMPACT PC',
    'ALL IN ONE', 'ALL-IN-ONE', 'AIO PC',
    
    # Retail indicators
    'BOXED PC', 'RETAIL PC', 'STORE PC',
    'COMPLETE PC', 'READY PC', 'TURNKEY PC',
    
    # Build indicators
    'CUSTOM BUILD', 'PRE-ASSEMBLED', 'PRE ASSEMBLED',
    'FACTORY ASSEMBLED', 'REFURBISHED PC'
]

# Keywords for "Boring" flag - indicates low customization/value
BORING_KEYWORDS = [
    'OFFICE PC', 'HOME OFFICE', 'BASIC PC', 'ENTRY LEVEL',
    'WORKSTATION', 'BUSINESS PC', 'CORPORATE PC',
    'SCHOOL PC', 'STUDENT PC', 'HOME PC',
    'STANDARD PC', 'REGULAR PC', 'BUDGET PC'
]


def is_prebuilt_pc(title: str, description: str = '') -> dict:
    """
    Check if a listing is for a prebuilt or mini PC.
    
    Returns dict with:
    - is_prebuilt: bool
    - is_boring: bool (low customization/value)
    - matched_keywords: list of matched terms
    - confidence: float (0-1)
    """
    text = f"{title} {description}".upper()
    
    result = {
        'is_prebuilt': False,
        'is_boring': False,
        'matched_keywords': [],
        'confidence': 0.0
    }
    
    # Check brand names
    for brand in PREBUILT_BRANDS:
        if brand in text:
            result['is_prebuilt'] = True
            result['matched_keywords'].append(brand)
            result['confidence'] = max(result['confidence'], 0.9)
    
    # Check keywords
    for keyword in PREBUILT_KEYWORDS:
        if keyword.upper() in text:
            result['is_prebuilt'] = True
            result['matched_keywords'].append(keyword)
            result['confidence'] = max(result['confidence'], 0.7)
    
    # Check "boring" indicators
    for keyword in BORING_KEYWORDS:
        if keyword.upper() in text:
            result['is_boring'] = True
            if keyword not in result['matched_keywords']:
                result['matched_keywords'].append(f"Boring: {keyword}")
    
    return result


def get_prebuilt_badge(is_prebuilt: bool, is_boring: bool) -> str:
    """Generate HTML badge for prebuilt PC."""
    if not is_prebuilt:
        return ''
    
    if is_boring:
        return '<span class="badge prebuilt-boring" style="background: #95a5a6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">😴 Boring</span>'
    else:
        return '<span class="badge prebuilt" style="background: #e74c3c; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">🏭 Prebuilt</span>'
