# GPU Page Tags Documentation

This document explains how the three primary deal/interest tags on the GPU page work:

- 🆕 **NEW**
- ✨ **FIRST**
- 🔥 **STEAL**

## Source file

All tag logic lives in `SS-WEBSITE/templates/gpu.html`, inside the `loadListings()` JavaScript function where each listing row is rendered.

## Data source

The page calls `/api/gpus?active=true&...` and enriches each listing with price history from `/api/price-history/<listing_id>`. Tags are computed entirely in the browser.

---

## 🆕 NEW

**Meaning:** The listing was imported in the most recent scraper import.

**Logic:**
```js
let isNewListing = item.is_new === true;
if (isNewListing) {
    dealBadge += `<span class="badge" ...>🆕 NEW</span>`;
}
```

**Backend support:** `app.py` `/api/gpus` computes `is_new` by comparing each listing's `first_seen_at` against the latest `first_seen_at` value across all GPU listings:

```python
latest_first_seen = max(row['first_seen_at'] for row in rows if row['first_seen_at'])
row_dict['is_new'] = (row['first_seen_at'] == latest_first_seen)
```

**Behavior:** A listing only gets the NEW badge during the import run in which it was first seen. After the next scrape, older listings are no longer "new".

---

## ✨ FIRST

**Meaning:** This is the first time the matched GPU model has ever appeared in the local database (across sessions).

**Logic:**
1. Load previously discovered models from `localStorage`:
   ```js
   const discoveredModelsKey = 'discovered_gpu_models';
   let discoveredModels = new Set(JSON.parse(localStorage.getItem(discoveredModelsKey)) || []);
   ```
2. For each listing, check if the model key is new:
   ```js
   const modelKey = item.gpu_model || item.title;
   const isFirstModelEver = modelKey && !discoveredModels.has(modelKey);
   if (isFirstModelEver && modelKey) {
       discoveredModels.add(modelKey);
       newModelsDiscovered.push(modelKey);
   }
   ```
3. Render the badge:
   ```js
   if (isFirstModelEver && modelKey) {
       dealBadge += `<span class="badge" ...>✨ FIRST</span>`;
   }
   ```
4. Persist the updated set back to `localStorage`:
   ```js
   localStorage.setItem(discoveredModelsKey, JSON.stringify([...discoveredModels]));
   ```

**Behavior:** Once a model has been seen, it will never show FIRST again on that browser. The badge is per-browser, not per-user, because it relies on `localStorage`.

---

## 🔥 STEAL

**Meaning:** The listing is priced at least 15% below the average price of its matched GPU model.

**Logic:**
```js
if (!isNewListing && item.price_stats && item.price_stats.below_avg) {
    const avgPrice = parseFloat(item.price_stats.avg);
    const currentPrice = item.price_eur;
    const savingsPct = ((avgPrice - currentPrice) / avgPrice * 100);
    if (savingsPct >= 15) {
        dealBadge += `<span class="badge" ...>🔥 STEAL</span>`;
    }
}
```

**Backend support:** `app.py` `/api/gpus` attaches `price_stats` to each listing by aggregating all active, unflagged listings with the same `matched_gpu_id`:

```python
SELECT matched_gpu_id, AVG(price_eur), MIN(price_eur), MAX(price_eur)
FROM listings
WHERE category = 'gpu' AND is_active = true AND flagged_listings IS NULL
GROUP BY matched_gpu_id
```

The API returns:
- `price_stats.avg`
- `price_stats.min`
- `price_stats.max`
- `price_stats.below_avg` (`current_price < avg`)
- `price_stats.percentile`

**Behavior:**
- STEAL only appears when the listing is **not** NEW (NEW takes precedence in badge stacking).
- Requires at least a 15% discount vs. the model average.
- If no `price_stats` are present (e.g., a unicorn listing with no comparable models), no STEAL badge is shown.

---

## Badge stacking order

Badges are appended to `dealBadge` in this order:
1. 🆕 NEW (if `is_new`)
2. ✨ FIRST (if first model ever)
3. 🔥 STEAL (if >= 15% below avg and not NEW)

The most visually prominent badge (STEAL) is rendered last, so it appears at the bottom of the overlay stack on the listing thumbnail.

---

## Related UI

- The same logic also computes a **price percentile bar** in the "Market Position" column.
- A **🦄 UNICORN** badge appears in "Market Position" when a listing is the only active, unflagged one for its `matched_gpu_id`.
- A **✅ BUY** badge appears when the current price equals the all-time minimum and the price history has more than one distinct value.

---

## Files touched

- `SS-WEBSITE/templates/gpu.html` — tag rendering logic
- `SS-WEBSITE/app.py` — `is_new` and `price_stats` computation for `/api/gpus`
