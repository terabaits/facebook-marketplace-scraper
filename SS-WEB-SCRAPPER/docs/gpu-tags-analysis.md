# GPU Page Tags Analysis — `NEW`, `FIRST`, and `STEAL`

Project: `SS-WEBSITE`  
File examined: `G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\app.py`  
Template examined: `G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\gpu.html`  
Report date: 2026-07-07

---

## 1. Overview of the three tags

| Tag | Meaning | Where computed | Rendering color |
|-----|---------|----------------|-----------------|
| **NEW** | This GPU listing was first seen on the most recent import date for the `gpu` category. | Server-side (`app.py`) | Blue badge `#3b82f6` with `🆕 NEW` |
| **FIRST** | This is the first time the user's browser has ever seen this `gpu_model` (or `title` as fallback) in the GPU table. | Client-side (`templates/gpu.html`) | Purple badge `#9333ea` with `✨ FIRST` |
| **STEAL** | The listing's price is at least 15% below the model's historical average **and** it is not a NEW listing. | Client-side (`templates/gpu.html`) | Red badge `#dc2626` with `🔥 STEAL` |

All three badges are rendered together as deal badges in the **Image** column of the GPU listings table.

---

## 2. `NEW` tag

### 2.1 What it means
A listing is marked `NEW` when its `first_seen_at` date equals the latest import date for any GPU listing in the database. In other words, the listing appeared for the first time during the most recent scrape/import batch.

### 2.2 Server-side computation

**Code location:** `app.py`, lines **145–167**

```python
def get_category_latest_import_date(category):
    """Get the latest import date for a specific category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT MAX(first_seen_at::date) as latest_date
            FROM listings
            WHERE category = %s
        """, (category,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    finally:
        cursor.close()
        conn.close()


def is_listing_new(listing_date, category):
    """Check if a listing is 'new' (from the latest import date for its category)."""
    if not listing_date:
        return False
    latest_import = get_category_latest_import_date(category)
    if not latest_import:
        return False
    # Compare just the date parts
    listing_date_only = listing_date.date() if hasattr(listing_date, 'date') else listing_date
    return listing_date_only == latest_import
```

**Important behavior:**
- It queries the database for **every call** (no caching of the latest import date inside this function).
- It compares only the date part, so any time on the same day is treated as `new`.
- `first_seen_at` is selected in the GPU query at `app.py` line **659** and assigned to `listing_dict['first_seen_at']`.

**Code location:** `app.py`, line **741**

```python
# Mark as new if this listing is from the latest import for GPU category
listing_dict['is_new'] = is_listing_new(listing_dict.get('first_seen_at'), 'gpu')
```

There is also a debug print at line **745**:

```python
if listing_dict['is_new']:
    print(f"[DEBUG NEW] {listing_dict['listing_id']}: first_seen={listing_dict['first_seen_at']}, is_new=True")
```

### 2.3 Frontend rendering

**Code location:** `templates/gpu.html`, lines **830–837**

```javascript
let isNewListing = item.is_new === true;

if (isNewListing) {
    // New listing from current import - show NEW badge
    dealBadge += `<span class="badge" style="background: #3b82f6; color: white; font-weight: bold;" title="New listing from current import!">🆕 NEW</span><br>`;
}
```

The badge is displayed in `imageOverlayBadges` in the top-right corner of the listing thumbnail at line **974**.

---

## 3. `FIRST` tag

### 3.1 What it means
`FIRST` indicates that the user's browser has never seen this GPU model (or title fallback) before **in any prior page load**. It is purely a client-side/browser-local concept and depends on `localStorage`.

### 3.2 How it is computed

**Code location:** `templates/gpu.html`, lines **776–789**

```javascript
// Track first occurrence of each GPU model - persist across sessions
const discoveredModelsKey = 'discovered_gpu_models';
let discoveredModels = new Set();
try {
    const stored = localStorage.getItem(discoveredModelsKey);
    if (stored) {
        discoveredModels = new Set(JSON.parse(stored));
    }
} catch (e) {
    console.error('Error loading discovered models:', e);
}

// Track new models discovered in this session
const newModelsDiscovered = [];
```

**Code location:** `templates/gpu.html`, lines **822–827**

```javascript
const modelKey = item.gpu_model || item.title;
const isFirstModelEver = modelKey && !discoveredModels.has(modelKey);
if (isFirstModelEver && modelKey) {
    discoveredModels.add(modelKey);
    newModelsDiscovered.push(modelKey);
}
```

At the end of the table rendering loop, the updated set is saved back to `localStorage` at lines **1041–1048**:

```javascript
if (newModelsDiscovered.length > 0) {
    try {
        localStorage.setItem(discoveredModelsKey, JSON.stringify([...discoveredModels]));
        console.log(`Saved ${newModelsDiscovered.length} newly discovered models to localStorage`);
    } catch (e) {
        console.error('Error saving discovered models:', e);
    }
}
```

### 3.3 Frontend rendering

**Code location:** `templates/gpu.html`, lines **839–844**

```javascript
if (isFirstModelEver && modelKey) {
    // First model ever discovered - show FIRST badge
    dealBadge += `<span class="badge" style="background: #9333ea; color: white; font-weight: bold;" title="First time this model appears!">✨ FIRST</span><br>`;
}
```

### 3.4 Edge cases / bugs
- **Per-browser, not per-user or per-database:** A model will show `FIRST` on the first browser that loads it, but not on a second browser because the `localStorage` state is different. Refreshing the same browser after it has been saved will no longer show `FIRST` for that model.
- **Title fallback:** If `item.gpu_model` is missing, the raw listing `title` is used. The same GPU model can therefore generate multiple keys (`title` vs. `gpu_model`) and may appear as `FIRST` twice.
- **No server coordination:** A model could have existed in the database for months but still show `FIRST` the first time a particular browser visits the GPU page.

---

## 4. `STEAL` tag

### 4.1 What it means
A listing is a `STEAL` when its current price is at least **15% below** the average price of all matched listings for that GPU model **and** the listing is **not** a `NEW` listing.

### 4.2 Backend support

The server provides `price_stats` per listing. The stats are computed from a separate aggregate query in `get_gpus()`:

**Code location:** `app.py`, lines **701–714**

```python
# Add price statistics for each GPU model (active-only or all listings)
gpu_stats = {}
flagged_clause = "AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)" if use_active_avg else ""
cursor.execute(f"""
    SELECT
        g.id,
        g.vendor,
        g.model,
        ROUND(AVG(l.price_eur)::numeric, 2) as avg_price,
        MIN(l.price_eur) as min_price,
        MAX(l.price_eur) as max_price,
        COUNT(*) as listing_count
    FROM listings l
    JOIN gpu_reference g ON l.matched_gpu_id = g.id
    WHERE l.category = 'gpu'
        {flagged_clause}
    GROUP BY g.id, g.vendor, g.model
""")
for row in cursor.fetchall():
    gpu_stats[row['id']] = dict(row)
```

These aggregates are attached to each listing at lines **716–733**:

```python
if listing_dict.get('matched_gpu_id') and listing_dict['matched_gpu_id'] in gpu_stats:
    stats = gpu_stats[listing_dict['matched_gpu_id']]
    listing_dict['price_stats'] = {
        'avg': stats['avg_price'],
        'min': stats['min_price'],
        'max': stats['max_price'],
        'below_avg': listing_dict['price_eur'] < stats['avg_price'],
        'percentile': round((listing_dict['price_eur'] - stats['min_price']) /
                          (stats['max_price'] - stats['min_price']) * 100, 1)
                          if stats['max_price'] > stats['min_price'] else 50,
        'listing_count': stats['listing_count']
    }
```

### 4.3 Frontend computation

**Code location:** `templates/gpu.html`, lines **846–857**

```javascript
if (!isNewListing && item.price_stats && item.price_stats.below_avg) {
    // STEAL: only show if price is at least 15% below average
    const avgPrice = parseFloat(item.price_stats.avg);
    const currentPrice = item.price_eur;
    const savingsPct = ((avgPrice - currentPrice) / avgPrice * 100);

    // Must be at least 15% below average to be a STEAL
    if (savingsPct >= 15) {
        dealBadge += `<span class="badge" style="background: #dc2626; color: white; font-weight: bold;" title="Price is ${savingsPct.toFixed(0)}% below average!">🔥 STEAL</span><br>`;
    }
}
```

### 4.4 Edge cases / bugs
- **STEAL is suppressed for NEW listings.** The condition `!isNewListing` means a brand-new listing that is dramatically underpriced will **not** get a `STEAL` badge, even though it might be the best deal.
- **Average includes the current listing itself.** Because `avg_price` is computed over all matched listings including the one being evaluated, a single very cheap listing can slightly drag down its own average, but the effect is usually small.
- **Division by zero not handled.** If `avgPrice` is `0`, `savingsPct` becomes `Infinity`; the `>= 15` check will still be `true` and it will render `Infinity%`. In practice this is unlikely because GPU prices are rarely zero.
- **`use_active_avg` toggle changes the average.** The average used for `STEAL` depends on whether the user has checked "Active-only averages". A flagged (scam/spam) listing can therefore appear or disappear as a `STEAL` based on a frontend checkbox, which may be confusing.

---

## 5. How the badges are rendered in the table

All badges are injected into the **Image** cell of each row:

**Code location:** `templates/gpu.html`, lines **963–981**

```javascript
const imageOverlayBadges = (dealBadge || priceDecreasedBadge)
    ? `<div style="position: absolute; top: 4px; right: 4px; display: flex; flex-direction: column; gap: 4px; z-index: 10;">${dealBadge}${priceDecreasedBadge}</div>`
    : '';

html += `
    <tr class="${rowClass}" ${clickHandler} title="Click to view listing details">
        <td class="listing-image-cell" style="position: relative;">
            ${imageOverlayBadges}
            ${imageUrl ? `<img src="${imageUrl}" alt="${gpuName}" class="listing-thumb" loading="lazy" onclick="event.stopPropagation(); showImageModal('${imageClickUrl}', '${gpuName}')">` : '<div class="listing-thumb-placeholder">📷</div>'}
        </td>
        ...
```

Badges appear stacked vertically in the top-right corner of the thumbnail.

---

## 6. Related code locations summary

| Concern | File | Lines | Description |
|---------|------|-------|-------------|
| Latest GPU import date | `app.py` | 139–153 | `get_category_latest_import_date()` |
| NEW logic helper | `app.py` | 165–173 | `is_listing_new()` |
| GPU query selects `first_seen_at` | `app.py` | 659 | Included in the `SELECT` clause |
| GPU stats aggregate | `app.py` | 701–714 | Computes avg/min/max/count per `matched_gpu_id` |
| NEW flag attached | `app.py` | 741 | `listing_dict['is_new'] = is_listing_new(...)` |
| NEW debug print | `app.py` | 745 | Logs when `is_new` is true |
| `FIRST` localStorage load | `templates/gpu.html` | 776–789 | Reads `discovered_gpu_models` |
| `FIRST` key detection | `templates/gpu.html` | 822–827 | Uses `gpu_model \|\| title` |
| `FIRST` badge render | `templates/gpu.html` | 839–844 | Purple badge |
| `NEW` badge render | `templates/gpu.html` | 830–837 | Blue badge |
| `STEAL` calculation | `templates/gpu.html` | 846–857 | 15% below avg, not new |
| Badges overlay | `templates/gpu.html` | 963–981 | In image cell top-right |

---

## 7. Notable observations and potential bugs

1. **N+1-ish database behavior for `NEW`**: `is_listing_new()` opens a new DB connection and runs a query for every GPU listing in the result set. With 100 listings, that means 100 identical `SELECT MAX(first_seen_at::date)...` queries. The result is the same for all of them on a given request; it could be computed once per request and passed in.

2. **`STEAL` hidden by `NEW`**: The strongest possible deal (a newly imported, very cheap GPU) will only show `NEW`, never `STEAL`, because `STEAL` is gated on `!isNewListing`.

3. **`FIRST` is browser-local and title-dependent**: It is not a server-side "first time this model appears in the database" tag. Clearing `localStorage` makes every model show `FIRST` again.

4. **Average used for `STEAL` changes with frontend filters**: The `use_active_avg` checkbox changes which rows are included in the average, so a listing can gain/lose `STEAL` depending on the user's checkbox state, not just market conditions.

5. **VRAM confusion in the filter code**: The filter multiplies the selected GB value by 1024 and compares it against `g.vram_gb`, but `format_vram()` later divides by 1024 to display it. There is an inline comment at line **630–631** noting that the column may actually contain MB, which can make the filter behavior hard to reason about.

6. **Price stats `percentile` bug when `max == min`**: The server returns `50` when all prices are identical, which is arbitrary but harmless.

---

## 8. Conclusion

- `NEW` is a **server-side, category-wide** freshness indicator driven by `first_seen_at`.
- `FIRST` is a **client-side, browser-local** novelty indicator driven by `localStorage`.
- `STEAL` is a **client-side, relative-price** deal indicator that requires `price_stats.below_avg` and a 15% discount, but is explicitly disabled for `NEW` listings.

The three tags work independently: a single listing can show `NEW` + `FIRST` simultaneously, but it can only show `STEAL` if it is **not** `NEW`. `FIRST` can also coexist with `STEAL` if the browser has not seen the model before and the price is low enough.
