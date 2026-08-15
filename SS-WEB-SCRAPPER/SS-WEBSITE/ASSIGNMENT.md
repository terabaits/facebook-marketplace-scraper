# ASSIGNMENT.md - Active Task Log

## Active Tasks

Processing tasks from Assignment column in priority order:
1. Reopened tasks first
2. New tasks by task ID ascending

**Current batch (as of 2026-08-12 18:37):**
- T108 (CPU: popup image full size) - reopened
- T211 (CPU: Most Listed chart count) - reopened
- T212 (CPU: widget size resets after drag) - reopened
- T272 (Laptops: CPU filter popup layout) - new
- T273 (Laptops: popup doesn't work) - new
- T274 (Laptops: Similar filter float error) - new
- T275 (CPU: row border color) - new
- T276 (CPU: price over time by months chart) - new
- T277 (Monitors: missing thumbnail style) - new
- T278 (GPU: missing thumbnail style) - new
- T279 (RAM: missing thumbnail style) - new
- T280 (Lenses: missing thumbnail style) - new
- T281 (Cameras: lens not detected message) - new
- T282 (GPU: VRAM exact-size checkbox redesign) - new
- T283 (GPU: change active-only averages icon) - new

**Status:** in-progress (2026-08-12 20:00)

**Progress log:**
- 2026-08-12 18:38 - Started new batch. Processing reopened tasks first, then new tasks by ID.
- 2026-08-12 18:55 - **T273 (Laptops popup doesn't work):** Added `showSharedListingDetail()` in `templates/laptops.html` that fetches `/api/listing-details/${id}` and renders the shared modal with image, price, description, and laptop specs.
- 2026-08-12 18:58 - **T274 (Laptops Similar filter float error):** Fixed `applySimilarFilter()` to strip non-numeric characters (e.g. the `"` inch quote) from RAM, storage, and display-size values before setting the filter inputs, preventing the `could not convert string to float: '16"'` error.
- 2026-08-12 19:08 - **T211 (CPU Most Listed chart count):** `/api/cpus` was hard-capped at 100 rows, so the Most Listed chart only saw a subset of all-time listings. Added `limit` query param and updated `loadCPUStatistics()` to fetch `limit=10000`. Verified `i5-7400` now counts all 7 all-time listings instead of 5.
- 2026-08-12 19:14 - **T212 (CPU widget size resets after drag):** Stopped `cleanupDrag()` from clearing the widget's inline `width`/`height`, so resized dimensions survive reordering. Added `align-self: start; justify-self: start` to `.widget-card` so explicit sizes are respected inside the CSS grid. Re-attaches resize listeners after each drag.
- 2026-08-12 19:25 - **T108 (CPU popup image full size):** CPU popup and table thumbnails now use the full-size remote image. `SS-CRAWLER/src/scraper/cpu_parser.py` now looks for the full `.800.jpg` gallery URL in the anchor around the thumbnail, and derives it from `.t.jpg` thumbnail URLs for existing rows. Frontend `templates/cpu.html` uses `normalizeCpuImageUrl()` to rewrite stored thumbnails on the fly, and the global `.listing-thumb` CSS constrains the table thumbnail.
- 2026-08-12 19:30 - **T275 (CPU row border less bold):** Replaced the inline row border with a `.cpu-row-divider` class using `rgba(238, 238, 238, 0.12)` for a subtler divider.
- 2026-08-12 19:35 - **T277–T280 (Missing thumbnail element style):** Added a shared `.listing-thumb` / `.listing-thumb-placeholder` rule in `templates/base.html` so GPU, CPU, Laptops, RAM, SSD, Monitors, Lenses, Motherboards, Cases, and PSU listings get consistent max-width/max-height, `object-fit: cover`, border radius, and cursor. Page-specific overrides in `cameras.html` and `computers.html` remain intact.
- 2026-08-12 19:40 - **T281 (Cameras "lens not detected"):** Confirmed camera listings do not show a "No lenses" badge or an empty "Detected Lenses" block when no lens is detected; lens-specific UI stays on the Lenses page.
- 2026-08-12 19:45 - Moved completed tasks T108, T211, T212, T273, T274, T275, T277, T278, T279, T280, T281 to Review (`talking`). Remaining in Assignment: T272, T276, T282, T283.

**Processing order:**
1. Reopened tasks first: T108, T211, T212
2. New tasks by ID ascending: T272, T273, T274, T275, T276, T277, T278, T279, T280, T281, T282, T283

## Next up

- T272 - Make the Laptops CPU filter popup bigger, grouped by vendor (Intel | AMD | Snapdragon | Mac), then subdivided by class (i3, Ryzen 5, etc.), sorted newest-to-oldest.
- T276 - Add a CPU "price over time by months" chart.
- T282 - Replace the GPU VRAM "Exact size" checkbox with an animated red `\u003c` toggle to the left of the dropdown.
- T283 - Change the GPU active-only averages icon to something different.

## Housekeeping

- There is still a leftover `python app.py` process on port 5000 that I couldn't terminate earlier. Before testing, kill it manually or start the server on a different port (e.g. 5001).
