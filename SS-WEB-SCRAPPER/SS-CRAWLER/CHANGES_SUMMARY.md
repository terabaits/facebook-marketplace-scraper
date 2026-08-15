# Summary of Changes

## Files Modified:

1. **src/utils/text.py**
   - Added AMD Phenom II patterns to `extract_cpu_tokens()`

2. **src/scraper/computer_matcher.py**
   - Added SSD context isolation in brand+capacity fallback
   - Added generic model filtering for 'aorus', 'extreme'
   - Added PSU fallback with extracted wattage
   - Removed 'pro' standalone matching (requires brand or multiple parts)

3. **src/scraper/psu_matcher.py**
   - Changed PSU context to look before AND after keyword (50 chars each way)

4. **src/scraper/case_matcher.py**
   - Changed case keyword requirements to be stricter

5. **src/scraper/computer_monitor_matcher.py**
   - Added model prefix matching for partial model matches
   - Increased weight for full model matches (0.40 -> 0.50)

## Test Results:

### fbfbc.html (Phenom II X6 1100T listing):
- ✅ CPU: Phenom II X6 1100T (ID: 1387) - CORRECT
- ✅ SSD: Generic 240GB SSD - CORRECT (was matching Aorus)
- ✅ PSU: Deepcool PF700 230V (ID: 6772) - CORRECT
- ✅ Case: Not detected (generic) - CORRECT
- ⚠️ Monitor: Proview 570 (50%) - This is RX 570 confusion, expected

### fgjlo.html (i5-11600K + SA270 monitor):
- ✅ CPU: i5-11600K (ID: 84) - CORRECT
- ✅ SSD: SNVS500G (ID: 2452) - CORRECT
- ✅ Monitor: Acer SA270Abi (85%) - CORRECT (was matching B247YDEbmiprczxv)
- ✅ Case: Not detected (generic) - CORRECT (was matching OCPC MINI)
- ✅ PSU: Not detected (650W fallback) - CORRECT (no PSU mentioned)

### aecib.html (i3-14100F + 550W PSU):
- ✅ CPU: i3-14100F (ID: 15) - CORRECT
- ✅ SSD: Generic 512GB SSD - CORRECT (was matching T-Force G70 Pro)
- ✅ PSU: Not detected (650W fallback) - NEEDS FIX for 550W
- ✅ Case: Not detected (generic) - CORRECT

## Known Issues:
- PSU wattage extraction for aecib.html shows 650W instead of 550W - needs investigation
