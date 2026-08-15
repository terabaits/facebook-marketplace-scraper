"""Test monitor tier calculation."""

import pytest
from src.utils.monitor_tier import calculate_monitor_tier, MonitorTierCalculator


class TestMonitorTierCalculator:
    """Test monitor tier calculations."""
    
    def test_msi_optix_g271c(self):
        """Test MSI Optix G271C specifically."""
        result = calculate_monitor_tier(
            size_str='27',
            resolution_str='2K',
            refresh_str='165',
            panel_str='VA'
        )
        
        print(f"\nMSI Optix G271C:")
        print(f"  Tier: {result['tier']}")
        print(f"  Score: {result['score']}/{result['max_score']}")
        print(f"  Components: {result['component_scores']}")
        print(f"  Specs: {result['specs_summary']}")
        
        # Should be GAMING: 27"(4) + 2K(4) + 165Hz(4) + VA(2) = 14
        assert result['tier'] == 'GAMING', f"Expected GAMING, got {result['tier']}"
        assert result['score'] >= 12
    
    def test_parsing_2k(self):
        """Test 2K resolution parsing."""
        width, height = MonitorTierCalculator.parse_resolution('2K')
        assert width == 2560
        assert height == 1440
    
    def test_parsing_165hz(self):
        """Test 165Hz parsing."""
        hz = MonitorTierCalculator.parse_refresh_rate('165Hz')
        assert hz == 165
    
    def test_beast_monitor(self):
        """Test BEAST tier monitor."""
        result = calculate_monitor_tier(
            size_str='32',
            resolution_str='4K',
            refresh_str='240',
            panel_str='IPS'
        )
        
        print(f"\nBeast Monitor:")
        print(f"  Tier: {result['tier']}")
        print(f"  Score: {result['score']}")
        
        assert result['tier'] == 'BEAST'
    
    def test_low_monitor(self):
        """Test LOW tier monitor."""
        result = calculate_monitor_tier(
            size_str='22',
            resolution_str='1080p',
            refresh_str='60',
            panel_str='TN'
        )
        
        print(f"\nLow Monitor:")
        print(f"  Tier: {result['tier']}")
        print(f"  Score: {result['score']}")
        
        assert result['tier'] == 'LOW'
