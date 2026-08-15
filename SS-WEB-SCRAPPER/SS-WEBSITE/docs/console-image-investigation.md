# Console Scraper Image Investigation

**Date:** 2026-07-27  
**Reporter:** user  
**Investigated by:** assistant

## Symptom

The `/consoles` page on the dashboard loaded listings, but no product images were shown. Console rows showed only the 📷 camera placeholder.

## Initial Findings

1. The browser console showed `ReferenceError: computeConsoleDealBadges is not defined`, crashing `loadListings`. This was fixed first by adding `computeConsoleDealBadges()` to `templates/consoles.html`.
2. After that fix, listings rendered but still had no images.

## Root Cause 1: Database Had No Image Links

The `console_listings` table stored console listings in a separate table from the generic `listings` table. A count query showed:

```
total: 604, with_url: 0, with_local: 0
```

Meanwhile, `SS-CRAWLER/images/consoles/` already contained 364 valid image files named `ss_<listing_id>_<hash>.jpg`. The files existed, but `console_listings.local_image_path` was `NULL` for every row.

**Fix:** A backfill script matched filenames by `listing_id` and wrote `images/consoles/<filename>` into `local_image_path` for those 364 rows.

## Root Cause 2: Template Only Checked `image_url`

The `consoles.html` template only rendered an `<img>` if `item.image_url` was truthy:

```javascript
${item.image_url ? (() => {
   ...
})() : '<div>...📷...</div>'}
```

Because `image_url` was `NULL` even when `local_image_path` existed, the placeholder was always shown.

**Fix:** Changed the condition to accept either field:

```javascript
${item.image_url || item.local_image_path ? (() => {
   const localPath = item.local_image_path ? item.local_image_path.replace(/\\/g, '/') : null;
   const imgUrl = localPath ? `/images/${localPath}` : item.image_url;
   ...
})() : '<div>...📷...</div>'}
```

After this, the 364 backfilled listings displayed their images.

## Root Cause 3: New Scraper Runs Created Broken `image_url` Values

When the user ran the console scraper again, new listings were added but still had no images.

### Investigation

A live fetch of the ss.com game-consoles search page showed a listing row like:

```html
<tr id="tr_57304710">
  <td class="msga2">
    <a href="/msg/lv/electronics/computers/game-consoles/bfglgd.html" id="im57304710">
      <img src="https://i.ss.com/gallery/8/1459/364577/72915383.th2.jpg" alt="" class="isfoto foto_list">
    </a>
  </td>
  ...
</tr>
```

ss.com serves `.th2.jpg` thumbnails and the full-size image is the same base name with `.800.jpg`, e.g.:

```
https://i.ss.com/gallery/8/1459/364577/72915383.800.jpg
```

The original `ConsoleScraper._extract_image()` in `SS-CRAWLER/src/scraper/console_scraper.py` was naive:

```python
full_src = src.replace('.thumb.', '.').replace('.th.', '.')
if full_src.endswith('.t.jpg'):
    full_src = full_src[:-6] + '.800.jpg'
elif full_src.endswith('.th2.jpg'):
    full_src = full_src[:-7] + '.800.jpg'
```

For `72915383.th2.jpg` this produced `72915383..800.jpg` (double dot), which is a 404 or placeholder. The `ImageDownloader` then logged **126 "Image too small" warnings** and only downloaded 5 images.

### Fix

Replaced the string slicing with regex replacements that remove the whole thumbnail suffix:

```python
full_src = src.replace('.thumb.', '.').replace('.th.', '.')
full_src = re.sub(r'\.t\.jpg$', '.800.jpg', full_src)
full_src = re.sub(r'\.th2\.jpg$', '.800.jpg', full_src)
```

A test parse of the live page now produces correct URLs like:

```
https://i.ss.com/gallery/8/1427/356621/71324144.800.jpg
```

## Resolution

1. **Console page load crash** — added missing `computeConsoleDealBadges()`.
2. **Existing images not shown** — backfilled `local_image_path` from files already in `SS-CRAWLER/images/consoles/` (364 rows) and changed the template to accept `image_url || local_image_path`.
3. **New scraper listings got broken images** — fixed `ConsoleScraper._extract_image()` to use regex-based suffix replacement instead of string slicing, preventing double-dot URLs.
4. **Backfill of broken/missing image URLs** — created `SS-CRAWLER/backfill_console_images_from_search.py`, which re-parses search pages (no slow detail-page fetches), downloads the correct `.800.jpg` images, and updates the database.

### Backfill Results

```
258 console listings needed images
150 listings found on first 5 search pages
28 images successfully downloaded and linked
230 remaining listings are not on current active pages (stale/old)
```

### Current Database State

```
total: 604
with image_url: 28
with local_image_path: 374
```

The 230 still-missing listings will receive images automatically when the fixed scraper sees them again in active search results.

## Files Changed / Created

| File | Change |
|------|--------|
| `SS-CRAWLER/src/scraper/console_scraper.py` | Fixed `_extract_image()` double-dot bug |
| `SS-WEBSITE/templates/consoles.html` | Added missing `computeConsoleDealBadges()`; image cell now checks `image_url \|\| local_image_path` |
| `SS-CRAWLER/backfill_console_images.py` | Backfilled `local_image_path` from existing `images/consoles/` files |
| `SS-CRAWLER/backfill_console_images_from_search.py` | Re-parses search pages and downloads correct `.800.jpg` images for rows missing `local_image_path` |
| `SS-WEBSITE/docs/console-image-investigation.md` | This document |

## Open Action

None for active listings. For the 230 stale listings, images will be recovered automatically on the next scraper pass that sees them in search results.
