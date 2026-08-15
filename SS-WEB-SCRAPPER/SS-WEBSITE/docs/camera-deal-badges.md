# Camera Deal Badges — Technical Design

**Date:** 2026-07-27  
**Scope:** `/cameras` page in SS-WEBSITE dashboard  
**Pattern:** Follows [`console-deal-badges.md`](./console-deal-badges.md) and [`lens-deal-badges.md`](./lens-deal-badges.md)

## Overview

The `/cameras` page implements the same two-layer badge system as `/consoles` and `/lenses`:

1. **Client-side overlay badges** (`NEW`, `STEAL`) on the listing thumbnail.
2. **Server-side rarity badge** (`UNICORN`) in the **Market Position** column, plus peer price statistics.

`FIRST` is intentionally disabled, consistent with the other category pages.

---

## Server-Side Changes

### `/api/cameras` in `SS-WEBSITE/app.py`

The camera endpoint returns an object wrapper `{"success": true, "listings": [...], "stats": {...}}` rather than a plain array, so the enrichment happens inside the existing listing loop before wrapping the response.

Added three enrichments to every camera listing:

- `first_seen_at` is now selected from `listings`.
- `is_new` is computed by comparing `first_seen_at::date` to the latest `first_seen_at::date` for all `category = 'camera'` listings.
- `is_unicorn` and `price_stats` are computed from an aggregate over all camera listings grouped by `matched_camera_id`.

### SQL for model statistics

```sql
SELECT
    l.matched_camera_id,
    ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
    MIN(l.price_eur) as min_price,
    MAX(l.price_eur) as max_price,
    COUNT(*) as listing_count
FROM listings l
WHERE l.category = 'camera'
  AND l.matched_camera_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM flagged_listings fl
      WHERE fl.listing_id = l.listing_id
        AND fl.is_active = true
  )
GROUP BY l.matched_camera_id
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

Key difference from lenses: the model key is `matched_camera_id`, and the reference table is `camera_reference` joined on `matched_camera_id::integer = c.id`.

---

## Client-Side Changes

### `SS-WEBSITE/templates/cameras.html`

Added `computeCameraDealBadges(item)`:

```javascript
function computeCameraDealBadges(item) {
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
- Market Position text and percentile-bar background use CSS variables (`var(--text-secondary)` and `var(--bar-bg)`) for dark-mode readability.

---

## Badge Semantics

| Badge | Location | Computed by | Condition |
|-------|----------|-------------|-----------|
| `NEW` | Image overlay | Server (`app.py`) | `first_seen_at::date == MAX(first_seen_at::date)` for camera category |
| `STEAL` | Image overlay | Client (`templates/cameras.html`) | `!NEW && price_stats.below_avg && savings >= 15%` |
| `UNICORN` | Market Position column | Server (`app.py`) | Exactly one unflagged listing for this `matched_camera_id` of all time |

`FIRST` is intentionally not implemented on the camera page.

---

## Files Changed

| File | Change |
|------|--------|
| `SS-WEBSITE/app.py` | `/api/cameras` selects `first_seen_at` and enriches with `is_new`, `is_unicorn`, `price_stats` |
| `SS-WEBSITE/templates/cameras.html` | Added `computeCameraDealBadges()`, overlay badges, Market Position column |
| `SS-WEBSITE/docs/camera-deal-badges.md` | This document |

---

## API Response Example

```json
{
  "success": true,
  "listings": [
    {
      "listing_id": "bfdnlk",
      "matched_camera_id": "21",
      "price_eur": 1050.0,
      "is_new": true,
      "is_unicorn": false,
      "price_stats": {
        "avg": 816.67,
        "min": 700.0,
        "max": 1050.0,
        "below_avg": false,
        "percentile": 100.0,
        "listing_count": 3
      }
    }
  ],
  "stats": { ... }
}
```

---

## Note on Active-Only Default

The `/cameras` page keeps the **Active only** checkbox checked by default. If no camera listings are currently active (e.g. scraper has not run recently), the page shows "No camera listings found". Uncheck **Active only** to see all camera listings and verify the badges.
