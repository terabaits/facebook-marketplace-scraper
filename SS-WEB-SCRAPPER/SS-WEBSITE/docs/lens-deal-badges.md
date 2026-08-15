# Lens Deal Badges — Technical Design

**Date:** 2026-07-27  
**Scope:** `/lenses` page in SS-WEBSITE dashboard  
**Pattern:** Follows [`console-deal-badges.md`](./console-deal-badges.md)

## Overview

The `/lenses` page implements the same two-layer badge system as `/consoles`:

1. **Client-side overlay badges** (`NEW`, `STEAL`) on the listing thumbnail.
2. **Server-side rarity badge** (`UNICORN`) in the **Market Position** column, plus peer price statistics.

`FIRST` is intentionally disabled, matching the console page decision.

---

## Server-Side Changes

### `/api/lenses` in `SS-WEBSITE/app.py`

Added three enrichments to every lens listing:

- `first_seen_at` is now selected from `listings`.
- `is_new` is computed by comparing `first_seen_at::date` to the latest `first_seen_at::date` for all `category = 'lens'` listings.
- `is_unicorn` and `price_stats` are computed from an aggregate over all lens listings grouped by `matched_lens_id`.

### SQL for model statistics

```sql
SELECT
    l.matched_lens_id,
    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
    MIN(l.price_eur) as min_price,
    MAX(l.price_eur) as max_price,
    COUNT(*) as listing_count
FROM listings l
WHERE l.category = 'lens'
  AND l.matched_lens_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM flagged_listings fl
      WHERE fl.listing_id = l.listing_id
        AND fl.is_active = true
  )
GROUP BY l.matched_lens_id
```

Per listing:

```python
item['is_unicorn'] = (listing_count == 1)
if listing_count > 1:
    item['price_stats'] = {
        'avg': avg_price,
        'min': min_price,
        'max': max_price,
        'below_avg': current_price < avg_price,
        'percentile': round((current_price - min_price) / (max_price - min_price) * 100, 1)
                      if max_price > min_price else 50,
        'listing_count': count
    }
```

Key difference from consoles: the model key is `matched_lens_id` instead of `matched_console_id`, and the table is the generic `listings` table filtered by `category = 'lens'`.

---

## Client-Side Changes

### `SS-WEBSITE/templates/lenses.html`

Added `computeLensDealBadges(item)`:

```javascript
function computeLensDealBadges(item) {
    let dealBadge = '';
    const isNewListing = item.is_new === true;

    if (isNewListing) {
        dealBadge += `<span class="badge" ...>🆕 NEW</span><br>`;
    }

    if (!isNewListing && item.price_stats && item.price_stats.below_avg) {
        const avgPrice = parseFloat(item.price_stats.avg);
        const currentPrice = item.price_eur;
        const savingsPct = ((avgPrice - currentPrice) / avgPrice * 100);
        if (savingsPct >= 15) {
            dealBadge += `<span class="badge" ...>🔥 STEAL</span><br>`;
        }
    }

    return dealBadge;
}
```

Also added:
- Overlay badge container in the image cell (`position: relative` + absolute-positioned badge stack).
- A new **Market Position** table column showing `UNICORN` or avg/min/max + percentile bar.
- Updated summary row colspan to account for the new column.
- Market Position text and percentile-bar background use CSS variables (`var(--text-secondary)` and `var(--bar-bg)`) so they remain readable in dark mode. The percentile fill keeps the purple gradient (`#667eea` → `#764ba2`) which is visible against the dark-mode bar background (`--bar-bg: #3a3a4a`).

### Dark-mode CSS variables used

These variables are defined in `base.html` for both light and dark themes:

```css
:root {
  --text-secondary: #6b7280;
  --bar-bg: #e5e7eb;
}

[data-theme="dark"] {
  --text-secondary: #9ca3af;
  --bar-bg: #3a3a4a;
}
```

By using the variables instead of hardcoded `#666` / `#888` / `#e5e7eb`, the Market Position column text and bar background automatically switch contrast for dark mode.

---

## Badge Semantics

| Badge | Location | Computed by | Condition |
|-------|----------|-------------|-----------|
| `NEW` | Image overlay | Server (`app.py`) | `first_seen_at::date == MAX(first_seen_at::date)` for lens category |
| `STEAL` | Image overlay | Client (`templates/lenses.html`) | `!NEW && price_stats.below_avg && savings >= 15%` |
| `UNICORN` | Market Position column | Server (`app.py`) | Exactly one unflagged listing for this `matched_lens_id` of all time |

`FIRST` is intentionally not implemented on the lens page, consistent with the console page.

---

## Files Changed

| File | Change |
|------|--------|
| `SS-WEBSITE/app.py` | `/api/lenses` selects `first_seen_at` and enriches with `is_new`, `is_unicorn`, `price_stats` |
| `SS-WEBSITE/templates/lenses.html` | Added `computeLensDealBadges()`, overlay badges, Market Position column |
| `SS-WEBSITE/docs/lens-deal-badges.md` | This document |

---

## API Response Example

```json
{
  "listing_id": "jphcx",
  "matched_lens_id": "Canon_24mm_F2.8_IS_USM",
  "price_eur": 270.0,
  "is_new": true,
  "is_unicorn": false,
  "price_stats": {
    "avg": 183.33,
    "min": 120.0,
    "max": 270.0,
    "below_avg": false,
    "percentile": 100.0,
    "listing_count": 3
  }
}
```
