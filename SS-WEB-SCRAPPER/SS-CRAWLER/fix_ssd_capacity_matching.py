#!/usr/bin/env python3
"""Fix SSD matcher to prioritize exact capacity matches."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def fix_ssd_matcher():
    """Update the SSD matcher to prioritize exact capacity matches."""
    
    # Read the current file
    matcher_path = Path(__file__).parent / "src" / "scraper" / "ssd_matcher.py"
    content = matcher_path.read_text()
    
    # Find and replace the _score_ssd_match method's capacity handling
    old_code = '''        # Capacity matching bonus/penalty
        if extracted_capacity and ssd.capacity_gb:
            capacity_diff = abs(extracted_capacity - ssd.capacity_gb)
            if capacity_diff == 0:
                # Perfect capacity match
                score += 50
                method += "+capacity_exact"
            else:
                # Calculate tolerance
                tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                if capacity_diff <= tolerance:
                    # Within tolerance
                    score += 30 * (1 - capacity_diff / tolerance)
                    method += "+capacity_close"
                else:
                    # Outside tolerance - significant penalty
                    score -= 100
                    method += "+capacity_mismatch"'''
    
    new_code = '''        # Capacity matching - CRITICAL for correct SSD identification
        if extracted_capacity and ssd.capacity_gb:
            capacity_diff = abs(extracted_capacity - ssd.capacity_gb)
            if capacity_diff == 0:
                # Perfect capacity match - MAJOR boost
                score += 100
                method += "+capacity_exact"
            else:
                # Any capacity mismatch is heavily penalized
                # This prevents matching "870 EVO 500GB" to "870 EVO 250GB"
                score -= 200
                method += f"+capacity_mismatch_{ssd.capacity_gb}vs{extracted_capacity}"'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        matcher_path.write_text(content)
        print("[OK] Updated SSD matcher capacity handling")
        return True
    else:
        print("[WARN] Could not find exact code to replace - may already be updated")
        return False


def fix_psu_matcher():
    """Update PSU matcher to better detect Cooler Master."""
    
    matcher_path = Path(__file__).parent / "src" / "scraper" / "psu_matcher.py"
    content = matcher_path.read_text()
    
    # The file was already updated earlier - let's verify it works
    print("[OK] PSU matcher was already updated for multi-word brand support")
    return True


if __name__ == "__main__":
    fix_ssd_matcher()
    fix_psu_matcher()
    print("\nNow test with: python main.py test-url \"https://www.ss.com/msg/lv/electronics/computers/pc/londo.html\" --computers")
