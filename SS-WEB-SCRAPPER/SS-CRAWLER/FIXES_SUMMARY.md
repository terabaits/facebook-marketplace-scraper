# Fix Summary for Listing 6 (alnnx)

## Issues Fixed

### Issue 1: RAM Not Matching Kingston HyperX 16 GB (ID 3289)
**Problem:** The listing text contains "HyperX" but not "Kingston" or "Fury". The `is_specific_ram` check in `computer_matcher.py` required both the brand (Kingston) AND a model keyword (like Fury) to be in the text, causing the match to fail.

**Solution:** Added special handling for HyperX in `computer_matcher.py`:
1. If "hyperx" is in the text and the RAM is a HyperX model, consider the brand matched (since HyperX is Kingston's gaming brand)
2. If "hyperx" is in the text and the RAM is a HyperX model, consider the model matched

**File:** `src/scraper/computer_matcher.py`
**Lines:** ~153-175 (in the `is_specific_ram` logic section)

### Issue 2: Motherboard Not Matching Asus TUF B450-PLUS GAMING (ID 7446)
**Problem:** The listing text has "B450-plus" but after normalization it becomes "b450plus" (no hyphen/space). The motherboard index only had "b450-plus" or "b450 plus" variants, not "b450plus", so exact matching failed.

**Solution:** Added hyphen-less variant generation in `motherboard_matcher.py`:
When building the index, also add variants without hyphens or spaces (e.g., "b450plus" in addition to "b450-plus")

**File:** `src/scraper/motherboard_matcher.py`
**Lines:** ~42-52 (in the `_build_index` method)

## Changes Made

### computer_matcher.py
```python
# Added after line ~156:
# Special handling: HyperX is Kingston's gaming brand - if "hyperx" is in text,
# consider it as having the Kingston brand (since HyperX = Kingston HyperX)
if not has_brand and 'hyperx' in ram_name_lower and 'hyperx' in normalized:
    has_brand = True

# Added after line ~169:
# Special handling: If "hyperx" is in text and the RAM is a HyperX model,
# consider it a model match even if "fury" is not explicitly mentioned
if not has_model_in_text and 'hyperx' in ram_name_lower and 'hyperx' in normalized:
    has_model_in_text = True
```

### motherboard_matcher.py
```python
# Added after line ~40:
# Also add variants without hyphens (e.g., "b450-plus" -> "b450plus")
# This handles cases where sellers write "B450PLUS" or "B450Plus"
model_no_hyphens = mb.model.replace('-', '').replace(' ', '')
norm_no_hyphens = normalize_text(f"{mb.brand} {model_no_hyphens}")
if norm_no_hyphens not in self.brand_model_names:
    self.all_names.append(norm_no_hyphens)
    self.brand_model_names[norm_no_hyphens] = mb
```

## Verification

The fixes have been tested with the actual listing text from https://www.ss.com/msg/lv/electronics/computers/pc/alnnx.html

### Test Results:
- ✓ RAM ID 3289 (Kingston HyperX 16 GB DDR4-4800) is now correctly matched
- ✓ Motherboard ID 7446 (Asus TUF B450-PLUS GAMING) is now correctly matched

## Listing Text Analysis

**Normalized Text:**
```
datori un orgtehnikadatori pardod pcdators ryzen 5 1600x ddr4 16gb hyperx 
motherboars asus tuf b450plus gaming ssd 128gb samsungwindows hdd 1tb wd blue 
gigabyte gtx 1060 3gb...
```

**Key Observations:**
- "hyperx" is present but "kingston" and "fury" are not
- "b450plus" is present (no hyphen) but "b450-plus" is not
- Both fixes address these text normalization edge cases
