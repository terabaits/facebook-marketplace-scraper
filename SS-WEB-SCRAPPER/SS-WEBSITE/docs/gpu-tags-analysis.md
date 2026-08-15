# GPU Page Tags Analysis

## Active Listings vs. Database Counts

The GPU page defaults to **Active only** listings. The database may contain many older/inactive versions of the same listing (for example, 28 `GeForce RTX 3070` rows in `listings` but only 4 active base-model listings). The page also:

- Excludes **flagged listings** from the main grid.
- Collapses listing versions: only the latest `listing_id` (`base_id` or `base_id_vN`) is shown; older versions remain in the database as price/description history.

To see all database rows, uncheck **Active only** in the filters.

### Market Position excludes flagged listings

Market Position and average-price calculations always exclude flagged listings, even when **Active-only averages** is enabled. Flagged listings are treated as bogus/wrong matches and should never influence price statistics.

---

## Overview
The GPU page displays four dynamic deal/discovery badges on each listing:
- **NEW** 🆕 — first appearance in the current import batch
- **FIRST** ✨ — first time this GPU model has ever been seen
- **STEAL** 🔥 — price is at least 15% below the model's average
- **BUY** ✅ — current price is the all-time lowest for this listing

---

## 1. NEW 🆕

**Logic (frontend):**
```javascript
let isNewListing = item.is_new === true;
if (isNewListing) {
    dealBadge += `<span class="badge" ...>🆕 NEW</span>`;
}
```

**Logic (backend):**
- `/api/gpus` sets `listing_dict['is_new'] = is_listing_new(listing_dict.get('first_seen_at'), 'gpu')`
- `is_listing_new()` compares `first_seen_at::date` with the latest import date for the `gpu` category:
  ```python
  listing_date_only == latest_import
  ```
- `get_category_latest_import_date('gpu')` returns `MAX(first_seen_at::date) FROM listings WHERE category = 'gpu'`.

**Meaning:** A listing is NEW only if it was first seen on the most recent GPU import day. It is **not** based on how recently it was posted to ss.com/andele.

---

## 2. FIRST ✨

**Logic (frontend only):**
```javascript
const modelKey = item.gpu_model || item.title;
const isFirstModelEver = modelKey && !discoveredModels.has(modelKey);
if (isFirstModelEver && modelKey) {
    discoveredModels.add(modelKey);
    newModelsDiscovered.push(modelKey);
    dealBadge += `<span class="badge" ...>✨ FIRST</span>`;
}
```

- `discoveredModels` is loaded from `localStorage` key `discovered_gpu_models` and persists across browser sessions.
- The key is the matched GPU model name (or raw listing title if no match).
- Once a model has been seen, it is stored in `localStorage` and will never show FIRST again on that browser.

**Meaning:** FIRST marks the first time the user's browser has seen that GPU model since the feature was introduced. It is client-specific, not global.

---

## 3. STEAL 🔥

**Logic (frontend):**
```javascript
if (!isNewListing && item.price_stats && item.price_stats.below_avg) {
    const avgPrice = parseFloat(item.price_stats.avg);
    const currentPrice = item.price_eur;
    const savingsPct = ((avgPrice - currentPrice) / avgPrice * 100);
    if (savingsPct >= 15) {
        dealBadge += `<span class="badge" ...>🔥 STEAL</span>`;
    }
}
```

**Logic (backend):**
- `/api/gpus` computes per-model statistics from `listings JOIN gpu_reference`:
  ```sql
  SELECT g.id, AVG(l.price_eur) as avg_price, MIN(l.price_eur) as min_price,
         MAX(l.price_eur) as max_price, COUNT(*) as listing_count
  ```
- `price_stats.below_avg = listing_dict['price_eur'] < stats['avg_price']`

**Meaning:** STEAL only appears when:
1. The listing is **not** NEW (NEW takes precedence), and
2. The listing price is below the model's average, and
3. The discount is **≥ 15%** below the average.

**Caveat:** The average is computed over **all** GPU listings for that model by default. The page has a toggle `use_active_avg` to include only active listings, but the backend query still uses all listings unless the toggle is enabled.

---

## 4. BUY ✅

**Logic (frontend):**
```javascript
let isAllTimeLowest = false;
if (item.history && item.history.length > 0) {
    const allPrices = item.history.map(h => h.price_eur);
    allPrices.push(item.price_eur);
    const minHistoryPrice = Math.min(...allPrices);
    if (Math.abs(item.price_eur - minHistoryPrice) < 0.01) {
        const uniquePrices = [...new Set(allPrices)];
        isAllTimeLowest = uniquePrices.length > 1;
    }
}
if (isAllTimeLowest) {
    dealBadge += `<span class="badge" ...>✅ BUY</span>`;
}
```

**Meaning:** BUY appears when:
1. The listing has price history, and
2. The current price equals the minimum price ever recorded, and
3. There has been price variation (at least two different prices in history).

This prevents BUY from showing on listings that always had the same single price.

---

## Priority / Display Order

Badges are appended in this fixed order:
1. NEW
2. FIRST
3. STEAL
4. BUY

NEW and FIRST can appear together. STEAL is suppressed for NEW listings. BUY can appear independently if price-history conditions are met.

---

## Backend Data Sources

| Badge | Backend Field | Frontend Computation |
|-------|--------------|----------------------|
| NEW | `is_new` | Direct use |
| FIRST | none (client state) | `localStorage` + `gpu_model` |
| STEAL | `price_stats.avg`, `price_stats.below_avg` | Frontend applies 15% threshold |
| BUY | `history[].price_eur` | Frontend compares all historical prices |

---

## Potential Issues / Notes

1. **NEW vs. STEAL exclusivity:** A new listing that is also a great deal will only show NEW, not STEAL. This may hide genuinely cheap new listings.
2. **FIRST is per-browser:** Clearing `localStorage` or using a different browser/device will reset FIRST badges.
3. **Average includes inactive/flagged:** By default, the average used for STEAL includes all listings. The `use_active_avg` toggle exists but may not be widely used.
4. **BUY requires history:** A brand-new listing with one price will not show BUY even if it's the cheapest available.
