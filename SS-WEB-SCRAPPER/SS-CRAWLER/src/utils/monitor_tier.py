"""Monitor quality tier calculator.

Calculates quality tiers based on monitor specifications:
- BEAST: 240Hz+, 4K+, 32"+ (ultimate gaming/pro)
- GAMING: 144-240Hz, 1440p+, 27"+ (competitive gaming)
- EDITORS: 4K, IPS/VA, 60Hz+ (content creation)
- MID: 1080p-1440p, 60-144Hz, 24-27" (mainstream)
- LOW: 1080p, 60Hz, <24" (basic)
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class MonitorSpecs:
    """Parsed monitor specifications."""
    size: Optional[float] = None  # inches
    width: Optional[int] = None   # pixels
    height: Optional[int] = None  # pixels
    refresh_rate: Optional[int] = None  # Hz
    panel_type: Optional[str] = None  # IPS, VA, TN, OLED


class MonitorTierCalculator:
    """Calculate monitor quality tier based on specs."""
    
    TIERS = {
        'BEAST': {
            'score': 5,
            'color': '#ff0000',  # Red
            'bg': '#ffcccc',
            'icon': '👑',
            'desc': 'Ultimate Gaming/Pro'
        },
        'GAMING': {
            'score': 4,
            'color': '#ff6b00',  # Orange
            'bg': '#ffe4cc',
            'icon': '🎮',
            'desc': 'Competitive Gaming'
        },
        'CREATOR': {
            'score': 3,
            'color': '#8b5cf6',  # Violet
            'bg': '#ede9fe',
            'icon': '🎨',
            'desc': 'Content Creation'
        },
        'EDITORS': {
            'score': 3,
            'color': '#9b59b6',  # Purple
            'bg': '#e8d5f2',
            'icon': '🎬',
            'desc': 'Photo/Video Editing'
        },
        'MID': {
            'score': 2,
            'color': '#3498db',  # Blue
            'bg': '#d6eaf8',
            'icon': '⚡',
            'desc': 'Mainstream'
        },
        'LOW': {
            'score': 1,
            'color': '#95a5a6',  # Gray
            'bg': '#ecf0f1',
            'icon': '💻',
            'desc': 'Basic'
        },
        'UNKNOWN': {
            'score': 0,
            'color': '#7f8c8d',
            'bg': '#f5f5f5',
            'icon': '❓',
            'desc': 'Unknown'
        }
    }
    
    @classmethod
    def parse_size(cls, size_str: Optional[str]) -> Optional[float]:
        """Parse size from string like '27"' or '27.5'"."""
        if not size_str:
            return None
        match = re.search(r'(\d+\.?\d*)', str(size_str))
        if match:
            return float(match.group(1))
        return None
    
    @classmethod
    def parse_resolution(cls, res_str: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """Parse resolution from string like '1920x1080' or '4K'"."""
        if not res_str:
            return None, None
        
        res_str = str(res_str).upper().strip()
        
        # Common resolutions
        resolutions = {
            '4K': (3840, 2160),
            'UHD': (3840, 2160),
            '2K': (2560, 1440),
            '1440P': (2560, 1440),
            'QHD': (2560, 1440),
            'WQHD': (3440, 1440),
            '1080P': (1920, 1080),
            'FHD': (1920, 1080),
            'FULL HD': (1920, 1080),
            '720P': (1280, 720),
            'HD': (1280, 720),
            '8K': (7680, 4320),
        }
        
        for key, val in resolutions.items():
            if key in res_str:
                return val
        
        # Try to parse WxH format
        match = re.search(r'(\d+)\s*x\s*(\d+)', res_str)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        return None, None
    
    @classmethod
    def parse_refresh_rate(cls, refresh_str: Optional[str]) -> Optional[int]:
        """Parse refresh rate from string like '144Hz' or '144'"."""
        if not refresh_str:
            return None
        match = re.search(r'(\d+)', str(refresh_str))
        if match:
            return int(match.group(1))
        return None
    
    @classmethod
    def get_panel_score(cls, panel_type: Optional[str]) -> int:
        """Get panel quality score."""
        if not panel_type:
            return 0
        panel = str(panel_type).upper()
        scores = {
            'OLED': 5,
            'MINI LED': 4,
            'IPS': 3,
            'VA': 2,
            'TN': 1
        }
        for key, score in scores.items():
            if key in panel:
                return score
        return 0
    
    @classmethod
    def calculate_score(cls, size: Optional[float], width: Optional[int], 
                       height: Optional[int], refresh: Optional[int],
                       panel: Optional[str]) -> Tuple[str, int, dict]:
        """
        Calculate monitor tier based on specs.
        Returns: (tier_name, total_score, component_scores)
        """
        scores = {
            'size': 0,
            'resolution': 0,
            'refresh': 0,
            'panel': 0
        }
        
        # Size scoring
        if size:
            if size >= 32:
                scores['size'] = 5
            elif size >= 27:
                scores['size'] = 4
            elif size >= 24:
                scores['size'] = 3
            elif size >= 22:
                scores['size'] = 2
            else:
                scores['size'] = 1
        
        # Resolution scoring
        if width and height:
            pixels = width * height
            if pixels >= 3840 * 2160:  # 4K+
                scores['resolution'] = 5
            elif pixels >= 2560 * 1440:  # 1440p
                scores['resolution'] = 4
            elif pixels >= 1920 * 1080:  # 1080p
                scores['resolution'] = 2
            else:
                scores['resolution'] = 1
        
        # Refresh rate scoring
        if refresh:
            if refresh >= 360:
                scores['refresh'] = 6
            elif refresh >= 240:
                scores['refresh'] = 5
            elif refresh >= 165:
                scores['refresh'] = 4
            elif refresh >= 144:
                scores['refresh'] = 3
            elif refresh >= 75:
                scores['refresh'] = 2
            else:
                scores['refresh'] = 1
        
        # Panel scoring
        scores['panel'] = cls.get_panel_score(panel)
        
        total = sum(scores.values())
        max_possible = 20  # 5+5+6+4
        
        # Determine tier based on total score and key specs
        if total >= 16 or (refresh and refresh >= 240 and scores['resolution'] >= 4):
            tier = 'BEAST'
        elif total >= 12 or (refresh and refresh >= 144 and scores['resolution'] >= 3):
            tier = 'GAMING'
        elif scores['resolution'] >= 4 and refresh and refresh >= 60 and (panel and 'IPS' in panel.upper()):
            tier = 'CREATOR'
        elif scores['resolution'] >= 4 and refresh and refresh >= 60:
            tier = 'EDITORS'
        elif total >= 6:
            tier = 'MID'
        elif total > 0:
            tier = 'LOW'
        else:
            tier = 'UNKNOWN'
        
        return tier, total, scores
    
    @classmethod
    def get_tier_badge(cls, tier_name: str) -> str:
        """Generate HTML badge for tier."""
        tier = cls.TIERS.get(tier_name, cls.TIERS['UNKNOWN'])
        return f"""
        <span class="monitor-tier-badge" 
              style="background: {tier['bg']}; 
                     color: {tier['color']}; 
                     border: 2px solid {tier['color']};"
              title="{tier['desc']}">
            {tier['icon']} {tier_name}
        </span>
        """
    
    @classmethod
    def get_specs_summary(cls, size: Optional[float], width: Optional[int],
                         height: Optional[int], refresh: Optional[int],
                         panel: Optional[str]) -> str:
        """Generate specs summary string."""
        parts = []
        if size:
            parts.append(f'{size:.1f}"')
        if width and height:
            # Simplify resolution display
            if width >= 3840:
                parts.append('4K')
            elif width >= 2560:
                parts.append('1440p')
            elif width >= 1920:
                parts.append('1080p')
            else:
                parts.append(f'{width}x{height}')
        if refresh:
            parts.append(f'{refresh}Hz')
        if panel:
            parts.append(str(panel))
        
        return ' • '.join(parts) if parts else 'Unknown specs'


def calculate_monitor_tier(size_str: Optional[str], resolution_str: Optional[str],
                           refresh_str: Optional[str], panel_str: Optional[str]) -> dict:
    """
    Convenience function to calculate monitor tier from raw strings.
    Returns dict with tier info for API response.
    """
    calc = MonitorTierCalculator
    
    size = calc.parse_size(size_str)
    width, height = calc.parse_resolution(resolution_str)
    refresh = calc.parse_refresh_rate(refresh_str)
    
    tier_name, score, component_scores = calc.calculate_score(
        size, width, height, refresh, panel_str
    )
    
    tier_info = calc.TIERS.get(tier_name, calc.TIERS['UNKNOWN'])
    
    return {
        'tier': tier_name,
        'score': score,
        'max_score': 20,
        'icon': tier_info['icon'],
        'color': tier_info['color'],
        'bg_color': tier_info['bg'],
        'description': tier_info['desc'],
        'component_scores': component_scores,
        'specs_summary': calc.get_specs_summary(size, width, height, refresh, panel_str),
        'badge_html': calc.get_tier_badge(tier_name)
    }
