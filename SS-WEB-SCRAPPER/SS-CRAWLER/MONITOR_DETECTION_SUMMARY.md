# Monitor Detection Feature - Implementation Summary

## Overview
Added support to detect if a monitor is included in a computer listing. This helps identify complete PC setups that include a display.

## Files Created/Modified

### 1. New Files Created

#### `src/scraper/computer_monitor_matcher.py`
- **Purpose**: Detects monitors mentioned in computer listings
- **Key Features**:
  - Detects explicit monitor mentions ("includes monitor", "komplekts ar monitoru")
  - Extracts monitor specs: size, resolution, refresh rate, panel type
  - Matches against monitor database or creates generic monitor entry
  - Estimates monitor price based on specs

#### `src/models/schemas.py` (Appended)
- Added `MonitorReference` schema
- Added `MonitorMatchResult` schema

#### `src/database/repository.py` (Appended)
- Added `MonitorRepository` class for database access

### 2. Files Modified

#### `src/scraper/computer_matcher.py`
- Added import for `ComputerMonitorMatcher` and `MonitorReference`
- Added `monitors` parameter to `__init__`
- Added monitor matching logic in `match()` method
- Added monitor fields to `ComputerMatchResult`

#### `src/scraper/computer_scraper.py`
- Added import for `MonitorRepository`
- Modified `initialize()` to load monitor references
- Passes monitors to `ComputerMatcher`

#### `src/models/computer_schemas.py`
- Added `monitor` field to `ComputerMatchResult`
- Added `monitor_confidence`, `monitor_method` fields
- Added `has_monitor` and `monitor_included` flags

## How It Works

### Detection Patterns
The matcher looks for:
1. **Explicit mentions**: "includes monitor", "komplekts ar monitoru", "+ monitor"
2. **Monitor brand/model**: Samsung, LG, Dell, etc. paired with size indicators
3. **Size patterns**: "24 inch", "27\"", etc. in monitor context

### Matching Logic
1. Extract monitor-specific text sections (avoid CPU/GPU model numbers)
2. Look for monitor keywords and size indicators
3. Match against database of 20,272 monitors
4. If no specific match found, create generic monitor based on extracted specs
5. Calculate estimated price based on size, resolution, refresh rate, panel type

### Price Estimation
Generic monitor pricing:
- **Base by size**: 22"=€80, 24"=€100, 27"=€180, 32"=€250
- **Resolution bonus**: +€80 for 1440p, +€150 for 4K, +€120 for ultrawide
- **Refresh rate bonus**: +€50 for 144Hz, +€30 for 120Hz, +€15 for 75Hz
- **Panel bonus**: +€200 for OLED, +€100 for Mini LED, +€20 for IPS

## Usage

### Testing
```bash
python test_monitor_detection.py
```

### In Computer Listings
When scraping computer listings, the matcher will now:
1. Detect if a monitor is mentioned
2. Match to specific monitor model or create generic entry
3. Add monitor to component breakdown
4. Include monitor price in total valuation

## Example Output

```
Gaming PC + Monitor
Description: Intel i5, GTX 1660. Komplekts ar LG 27GL850 monitoru.

Result:
  [OK] DETECTED: LG 27GL850
  Size: 27", Resolution: 2560x1440
  Confidence: 80%, Method: brand+model+size
  Estimated Price: €230
```

## Integration Notes

The monitor detection integrates seamlessly with the existing computer scraper:
- Works alongside CPU, GPU, RAM, SSD, PSU, Case, Motherboard matching
- Adds monitor to the price breakdown calculation
- Flags listings that include monitors for special attention

## Database Schema

### monitor_models table (already exists)
```sql
- id: Primary key
- brand: Monitor brand (Samsung, LG, etc.)
- model: Model name/number
- size: Screen size in inches
- resolution: Display resolution
- refresh_rate: Refresh rate in Hz
- panel_type: IPS, VA, TN, OLED, etc.
- normalized_name: For text matching
- search_keywords: Array of searchable terms
```

## Future Enhancements

1. **Multiple Monitor Detection**: Detect "dual monitor" or "2x monitor" setups
2. **Monitor Stand/Arm Detection**: Detect if monitor includes stand or arm
3. **Cable Detection**: Check if cables (HDMI, DisplayPort) are included
4. **External Price Lookup**: Fetch actual market prices for specific monitor models
