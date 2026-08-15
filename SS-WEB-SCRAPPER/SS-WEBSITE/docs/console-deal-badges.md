# Console Deal Badges — Technical Design

**Date:** 2026-07-27  
**Scope:** `/consoles` page in SS-WEBSITE dashboard

## Overview

The `/consoles` page now mirrors the GPU page deal-badge system, except that `FIRST` is intentionally disabled per product decision. There are **two independent badge layers**:

1. **Client-side overlay badges** (`NEW`, `STEAL`) rendered on the listing thumbnail.
2. **Server-side rarity badge** (`UNICORN`) rendered in the **Market Position** column, plus peer price statistics.

The layers are intentionally separated: `NEW`/`STEAL` depend on browser state and current import, while `UNICORN` depends only on the global inventory in PostgreSQL.

---

## Client-Side Badges (overlay on image)

All client-side logic lives in `templates/consoles.html` inside `loadListings()` and `computeConsoleDealBadges(item, isFirstModelEver)`.

### `NEW` — server-provided, import-relative

- **Source:** API field `item.is_new`.
- **Computation in `app.py`:** `first_seen_at::date == MAX(first_seen_at::date)` over **all** `console_listings`.
- **Visual:** blue badge `🆕 NEW`.
- **Rule:** A listing is NEW only for the single most-recent import day of the console category. It disappears on the next scraper run that brings newer listings.

### `STEAL` — client-computed, price-relative

- **Source:** `item.price_stats` (server-provided) + `item.price_eur`.
- **Computation:** `!isNewListing && price_stats.below_avg && savingsPct >= 15%`.
- **Visual:** red badge `🔥 STEAL`.
- **Rule:** A STEAL is suppressed for NEW listings. This avoids marking every freshly-imported cheap listing as a STEAL before the model average has stabilized.

### `FIRST` — disabled on consoles

The GPU/CPU pages use `localStorage` (`discovered_*_models`) to show a purple `✨ FIRST` badge the first time a browser sees a model. For consoles this is intentionally skipped; the helper functions remain available in `templates/consoles.html` but are not called during render.

### `BUY` — not implemented

The GPU page declares an `isAllTimeLowest` variable but never renders a BUY badge. Consoles follows the same pattern: BUY is reserved for future work that requires per-listing price history (e.g. `price_changes` array) to be included in the API response.

---

## Server-Side Badge (`UNICORN`)

The UNICORN badge is fundamentally different from the overlay badges.

### Definition

A console listing is a **UNICORN** when its matched console model has **exactly one listing in `console_listings` of all time** (excluding flagged listings).

### Why it is different

| Aspect | NEW / STEAL | UNICORN |
|--------|-------------|---------|
| **Decision layer** | Client (browser) | Server (`app.py`) |
| **Data scope** | Current import + browser history | All-time inventory in PostgreSQL |
| **Persistence** | Ephemeral for NEW/STEAL | Database state |
| **Input fields** | `is_new`, `price_stats`, `price_eur` | `matched_console_id`, aggregate COUNT |
| **Visual location** | Overlay on thumbnail | Dedicated **Market Position** column |

Note: `FIRST` (per-browser localStorage) is available in the helper functions but disabled for consoles.

### SQL implementation in `/api/consoles`

```sql
SELECT
    cl.matched_console_id,
    ROUND(AVG(cl.price_eur)::numeric, 2) as avg_price,
    MIN(cl.price_eur) as min_price,
    MAX(cl.price_eur) as max_price,
    COUNT(*) as listing_count
FROM console_listings cl
WHERE cl.matched_console_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = cl.listing_id)
GROUP BY cl.matched_console_id
```

Then per listing:

```python
listing_dict['is_unicorn'] = (listing_count == 1)
```

When `listing_count == 1` we deliberately set `price_stats = None` because peer averages/ranges/percentiles are meaningless for a single listing.

### Rendering

The **Market Position** column shows either:

- `🦄 UNICORN` gradient badge if `is_unicorn` is true.
- Avg / min / max price and a percentile bar if `price_stats` exists.
- "No price data" if the listing is unmatched or the only peer data is unavailable.

---

## API Changes

`/api/consoles` now enriches each listing with:

```json
{
  "is_new": true | false,
  "is_unicorn": true | false,
  "price_stats": {
    "avg": 205.90,
    "min": 139.00,
    "max": 320.00,
    "below_avg": false,
    "percentile": 55.8,
    "listing_count": 31
  }
}
```

These fields are computed after the SQL result set is fetched, so no schema changes are required.

---

## Files Changed

| File | Change |
|------|--------|
| `SS-WEBSITE/app.py` | `/api/consoles` now computes `is_new`, `is_unicorn`, and `price_stats` |
| `SS-WEBSITE/templates/consoles.html` | Added `computeConsoleDealBadges()`, FIRST tracking via `localStorage`, Market Position column, UNICORN rendering |

---

## Future Implementation Checklist

When adding deal badges to a new category page, replicate this structure:

1. **Server API enrichment**
   - Compute latest `first_seen_at` date for `is_new`.
   - Aggregate by matched model ID for `price_stats` and `is_unicorn`.
   - Exclude flagged listings from unicorn/model aggregates.

2. **Client helpers**
   - `compute<Category>DealBadges(item)` for `NEW`/`STEAL`.
   - `FIRST` is optional; add `loadDiscovered<Category>Models()` / `saveDiscovered<Category>Models()` only if you want per-browser first-discovery badges.

3. **Rendering**
   - Overlay badges on the listing image.
   - Put `UNICORN` and price percentile in a separate **Market Position** column so users understand it is a different kind of signal.
