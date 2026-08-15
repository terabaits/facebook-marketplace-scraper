# Remaining Issues to Fix

## Current Status:

### fbfbc.html (Phenom II X6 1100T)
- ✅ CPU: Phenom II X6 1100T (ID 1387) - CORRECT
- ✅ GPU: Radeon RX 570 (ID 287) - CORRECT  
- ✅ SSD: Generic 240GB - CORRECT
- ✅ PSU: Deepcool PF700 (ID 6772) - CORRECT
- ✅ Case: Generic - CORRECT
- ✅ Monitor: Not detected - CORRECT (was Proview 570)
- ❌ Motherboard: Gigabyte Aorus Pro Wifi (ID 6609, AM4) - WRONG
  - Text says "Msi mātesplate" - no specific model
  - Should be: Generic MSI AM3 motherboard or fallback
  
### fpokc.html (i5-13600)
- ✅ CPU: i5-13600 (ID 31) - CORRECT
- ✅ RAM: 32GB DDR4 - CORRECT (specific RAM not matched yet)
- ❌ PSU: Gigabyte PB500 (ID 7286) - WRONG
  - Text says "PSU: OCZ 500W (OCZ500MXSP)"
  - Should be: ID 7627 (OCZ StealthXstream II 500W)
- ❌ Monitor: HP 32 (50%) - WRONG
  - Text doesn't mention monitor
  - Should be: Not detected

### lpmim.html (Ryzen 5600G)
- ✅ CPU: Ryzen 5 5600G (ID 313) - CORRECT (was 5600)
- ✅ SSD: Generic 500GB - CORRECT (was X8)
- ❌ PSU: Corsair CX (ID 6500, 550W) - WRONG
  - Text says "Corsair CX750M PSU"
  - Should be: ID 6532 (Corsair CX750M 750W) or 6502 (Corsair CX 750W)
- ✅ Monitor: Not detected - CORRECT

## Fixes Needed:

1. **Motherboard fallback when no specific model**: Currently matching "Gigabyte Aorus Pro Wifi" from GPU text instead of using generic MSI AM3 fallback

2. **PSU matching for OCZ**: OCZ brand not being detected in fpokc.html

3. **PSU wattage extraction for model names**: CX750M should extract 750W

4. **Monitor false positive (HP 32)**: Need to check why HP 32 is matching

## Files to Modify:
- src/scraper/computer_matcher.py (PSU wattage extraction)
- src/scraper/psu_matcher.py (OCZ brand detection)
- src/scraper/motherboard_matcher.py (context isolation)
- src/scraper/computer_monitor_matcher.py (false positive filtering)
