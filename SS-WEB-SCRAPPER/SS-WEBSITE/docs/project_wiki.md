# SS-WEB-SCRAPPER Project Wiki

Living documentation for the scraper + dashboard stack. Use the sidebar to jump to a section.

[TOC]

---

## 1. What This Wiki Covers

This page explains:

- The moving parts of `SS-WEB-SCRAPPER` (crawlers, matchers, database, dashboard).
- The architecture of shared features such as **flagging**, **charts**, **pop-up detail modals**, and **deal badges**.
- A short analysis of each dashboard page: what it shows and what makes it unique.
- Recent changes and recurring pitfalls so future debugging is faster.

If you update behavior in `app.py`, a template, or a matcher, add a note here.

---

## 2. Repository Layout

```
G:\Github\SS-WEB-SCRAPPER
├── SS-CRAWLER/                 # Data collection pipeline
│   ├── src/scraper/            # Per-category scrapers
│   ├── src/database/           # Repository layer + schema files
│   ├── src/models/             # Pydantic schemas
│   ├── images/                 # Downloaded listing images
│   ├── link_gpu_passmark.py    # PassMark ↔ GPU reference linker
│   └── gpu_benchmark_reference.csv
└── SS-WEBSITE/                 # Flask dashboard
    ├── app.py                  # All routes + API
    ├── templates/              # Jinja2 HTML pages
    ├── static/                 # CSS/JS
    ├── data/                   # Project board JSON
    ├── docs/                   # This wiki + analysis pages
    └── board_logger.py         # Structured project-board logging
```

### Data flow (high level)

1. **Scrape** – Selenium/requests pull listings from sources such as *andele*.
2. **Match** – Normalized title tokens are compared against reference tables (`gpu_reference`, `cpu_reference`, `ram_reference`, `ssd_reference`, `case_reference`, `psu_reference`, `motherboard_reference`, `console_reference`, `lens_reference`, etc.).
3. **Store** – Listings land in PostgreSQL; images are saved to `SS-CRAWLER/images/<category>/` and referenced by `listings.local_image_path`.
4. **Flag** – Bad/spam listings are recorded in `flagged_listings` and excluded from stats and listing tables.
5. **Serve** – Flask reads the active rows, computes stats on the fly, and returns JSON/HTML.
6. **Act** – The project board tracks bugs, improvements, and scraper maintenance.

---

## 3. Shared Dashboard Architecture

Features that appear on multiple pages are implemented once in `app.py` + `templates/base.html` and reused by every category page.

### 3.1 Flagging

**Database table:** `flagged_listings`

Current columns:

| Column | Purpose | Example |
|--------|---------|---------|
| `listing_id` | Source listing identifier | `fxkcn`, `doijd` |
| `category` | **Listing category** (not flag category). Mirrors `listings.category` or `computer_listings.category` for grouping in the admin filter. | `computer`, `ram`, `gpu`, `lens` |
| `reason` | **Flag reason category** — a machine-friendly tag describing *what kind of problem* the flag represents. | `ssd_mismatch`, `wrong_model`, `spam`, `component_missing`, `skip_filter` |
| `flag_comment` | **Human-readable note** — the free-form comment left by the user with extra context. | `Should have matched SSD ID 602; PSUs also missed.` |
| `flagged_at` | Timestamp when the flag was created | `2026-07-28 13:04:00` |
| `title`, `price_eur`, `seller_location`, `listing_url`, `image_url` | **Snapshot columns** — copied from the source listing at flag time so the admin CSV export still works if the listing is later deleted or moved. |

#### `reason` vs `flag_comment`

- **`reason`** is the **flagging category**. Think of it like a ticket type: it tells the scraper/dashboard team what class of issue to fix. It should be a short, stable slug such as `ssd_mismatch` or `spam`.
- **`flag_comment`** is the **comment that is left**. It is the human-readable detail: IDs, explanations, seller phrases to skip, etc.

When a user flags from the SSD page, the UI already works this way:

1. User picks a radio button for `flag-reason` (`ssd_mismatch`, `wrong_price`, `sold`, `spam`, `other`, `skip`).
2. User optionally fills the `flag-comment` textarea.
3. The page builds `finalComment` from `reason + comment` and sends both `reason` and `comment` to `/api/flag-listing`.

The admin panel and other category pages should eventually use the same pattern: a **reason/category picker** plus an optional **comment box**.

#### Recommended flag reason taxonomy

Based on an analysis of 109 existing flag texts, the most common problem classes are:

| Reason slug | When to use | Typical comment pattern |
|-------------|-------------|------------------------|
| `wrong_model` | The scraper matched the wrong reference model. | `This is a 2080 Ti, not 2080`, `GPU is the 8 GB variant, not 6 GB` |
| `component_missing` | A component that should have been detected was not matched. | `Why wasn't the SSD matched to ID 602?`, `CPU was not matched` |
| `ssd_mismatch` | SSD-specific wrong/missing detection. | `SSD information is incorrect`, `No SSD in this listing` |
| `ram_mismatch` | RAM-specific wrong/missing detection (capacity, type, laptop/DDR3/server). | `Scrapper found 16 GB, should be 32 GB`, `This is DDR3`, `laptop ram` |
| `motherboard_mismatch` | Motherboard not matched or wrong board matched. | `Why wasn't motherboard matched with ID 6215?` |
| `psu_mismatch` | PSU not matched or wrong PSU matched. | `There is no PSU in this listing; should have fallen back` |
| `case_mismatch` | Case not matched or wrong case matched. | `Why wasn't the case matched to ID 3334?` |
| `gpu_mismatch` | GPU not matched or wrong GPU matched. | `There is no GPU in this build` |
| `cpu_mismatch` | CPU not matched or wrong CPU matched. | `Why CPU was not matched` |
| `monitor_mismatch` | Monitor not matched or wrong monitor matched. | |
| `add_to_database` | A reference part is missing from the reference table. | `Add Corsair Vengeance RGB RS 32 GB DDR4-3200 to database` |
| `skip_filter` | The listing should be filtered out by a future scraper rule. | `Skip listings that say "planetētdators"`, `Skip listings with "Jauns"` |
| `spam_scam` | Obvious spam, scam, fake, or business listings. | `SPAM/SCAM: Interneta veikals`, `fake` |
| `vr_console_accessory` | Console/VR accessory handling issue. | `Includes PlayStation VR` |
| `laptop_ram` | Laptop/SODIMM/server RAM edge case. | `laptop memory`, `server ram` |
| `other` / `user_flagged` | Catch-all when none of the above apply. | `User flagged` |

#### Current behavior

- Almost every listing table row has a **🚩 Flag** button.
- Clicking it calls `POST /api/flag-listing` with `{listing_id, reason, comment}`.
- `app.py` stores a snapshot of the listing at flag time and inserts/updates `flagged_listings`.
- Most pages remove the flagged row client-side and reload the table so filters/stats refresh.
- Every stats query uses `AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)` to keep flagged items out of averages and badge calculations.

**Why it matters:** A single mispriced or miscategorized listing can distort a whole model’s average price. Flagging is the quick fix. Keeping `reason` as a separate category makes it possible to count which scraper/matcher problems happen most often and prioritize fixes.

### 3.2 Listing Detail Pop-up

File: `templates/base.html` contains `showSharedListingDetail()`.

The modal is reused by GPU, CPU, Computers, Motherboards, Monitors, RAM, Lenses, SSDs, PSUs, Cases, Consoles, and PC Builder pages. It shows:

- The listing image (`/images/<category>/<filename>`).
- Current price vs. previous price (with change arrow).
- Current description vs. previous description with a simple word-level diff.
- Price-history table.
- A link to the original source.
- A **Flag** button.
- For monitors: a calculated **tier badge** (BEAST / GAMING / EDITORS / MID / LOW) based on size, resolution, refresh rate, and panel type.

**Key client-side cache:** `sharedListingCache` prevents repeated fetches when a user opens the same listing twice.

### 3.3 Charts

Charts are rendered with **Chart.js**. Data comes from dedicated `/api/*-stats` endpoints. Common pattern:

```
/api/<category>-stats  →  SQL CTEs  →  JSON  →  Chart.js canvas
```

Examples:

- `/api/gpu-performance-stats` – scatter, vendor bars, value buckets.
- GPU page also has Price vs G3D and Price-per-G3D-point charts.

**Chart resilience rules we learned the hard way:**

1. Always wrap the `<canvas>` in a fixed-height container (`.perf-chart-box { height: 250px }`). `responsive: true` + `maintainAspectRatio: false` without a fixed container causes an infinite resize loop.
2. Cap dataset size server-side (e.g. top 10 models) and disable animations to keep the page fast.
3. Use small `pointRadius` for dense scatter plots.

### 3.4 Deal Badges

Badges are calculated in two places:

| Badge | Meaning | Where computed |
|-------|---------|----------------|
| **NEW** | First seen in the current import batch. | Backend (`is_listing_new()`). |
| **STEAL** | Price is ≥15% below the model average and the listing is not NEW. | Backend `price_stats`. |
| **UNICORN** | Exceptional value percentile; computed from active+unflagged listings only. | Backend `price_stats` (currently beta until pipeline is fixed). |

**Deprecated badges (2026-07-24):** **FIRST** (client-only, device-specific) and **BUY** (redundant with STEAL/UNICORN). See Section 14.2 for the full contract.

Badge rendering is page-specific. GPU and CPU pages overlay badges on the listing image. Some pages (e.g., Motherboards) render them in a dedicated column.

### 3.5 Dark Mode

- Toggle lives in the top nav.
- Theme is saved in `localStorage` as `theme` (`light` or `dark`).
- `data-theme` attribute is set on `<html>`; CSS variables switch background/text/border colors.

### 3.7 Column Customization (Gear Icon)

A gear-icon dropdown on some listing pages lets users reorder table columns and toggle column visibility. State is persisted in `localStorage`.

| Page | Gear icon | Persistence key |
|------|-----------|-----------------|
| GPU  | ✅        | `gpuColumnSettings` (implied by page naming) |
| CPU  | ✅        | `cpuColumnSettings` |
| RAM  | ✅        | `ramColumnSettings` / `enableRAMColumnCustomization` |
| Others (Motherboards, SSDs, PSUs, Cases, Lenses, Computers, Monitors, Consoles) | ❌ | — |

Implementation notes:
- The dropdown is rendered near the page title/filter bar.
- Required columns (e.g., GPU name) are disabled and cannot be hidden.
- Drag handles reorder columns; checkboxes toggle visibility.
- Dark-mode overrides for the dropdown live in page-specific `<style>` blocks (`[data-theme="dark"] .column-settings-dropdown`, `.column-option`, etc.).

### 3.8 Admin Page Toggles

The **Admin** page exposes several `localStorage`-backed switches that affect other pages:

| Toggle | localStorage key | Affected pages | Effect |
|--------|------------------|----------------|--------|
| Show listing IDs | `showListingId` | Base modal, GPU, Lenses, Motherboards | Adds a small `Listing ID: …` badge to the detail modal. |
| Show GPU matched ID | `showGPUId` | Base modal, GPU | Shows `GPU ID: …` badge when a GPU is matched. |
| Show CPU matched ID | *(not implemented)* | — | Planned; currently no page reads `showCPUId`. |
| Show delete buttons | `showDeleteButtons` | GPU detail modal, Admin | Adds a 🗑️ Delete button to the detail modal. |
| Show source dots | `showSourceDots` | GPU, CPU, Admin | Renders a colored source indicator dot next to the GPU/CPU name. |
| Show summary fields | `showSummaryFields` | CPU, GPU, SSD | Reveals a table-footer summary row with total/avg/count. |
| Show "GeForce" in NVIDIA names | `showGeForceInGPUName` | GPU | When unchecked, strips `GeForce ` from NVIDIA model names in the GPU column. |
| Enable RAM column customization | `enableRAMColumnCustomization` | RAM | Turns on the gear-icon column customization dropdown for RAM. |

The toggles are read directly in page JavaScript; there is no centralized settings store. **Migration in progress (2026-07-24):** all admin and display preferences are moving under a single versioned key `ss_settings_v1` with a one-time migration helper. See Section 12.6 for the migration map.

### 3.9 Feature Implementation Matrix

| Feature | GPU | CPU | Computers | Motherboards | Monitors | RAM | Lenses | SSDs | PSUs | Cases | Consoles | PC Builder | Models | Admin |
|---------|-----|-----|-----------|--------------|----------|-----|--------|------|------|-------|----------|------------|--------|-------|
| Listing table | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Detail modal | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Flag button | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| NEW badge | ✅ | ✅ | ❓ | ✅ | ❓ | ✅ | ❓ | ✅ | ✅ | ✅ | ❓ | — | — | — |
| STEAL badge | ✅ | ✅ | ❓ | ✅ | ❓ | ❓ | ❓ | ❓ | ✅ | ✅ | ❓ | — | — | — |
| UNICORN badge | ✅ | ✅ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | — | — | — |
| Gear icon (column reorder/hide) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |
| Price stats (avg/min/max) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Charts / visual stats | ✅ | ✅ | ❓ | ✅ | ✅ | ✅ | ✅ | ✅ | ❓ | ❓ | ❓ | ❓ | ❓ | ✅ |
| Dark-mode overrides | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin toggle consumer | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — |

Legend: ✅ implemented, ❌ not implemented, ❓ implementation status uncertain / needs verification.

### 3.10 Dark Mode Design System

CSS variables are defined in `templates/base.html` under `:root` and overridden under `[data-theme="dark"]`.

Key variables:

| Variable | Light | Dark | Purpose |
|----------|-------|------|---------|
| `--bg-color` | `#f5f7fa` | `#1a1a2e` | Page background |
| `--text-color` | `#333` | `#e0e0e0` | Primary text |
| `--card-bg` | `white` | `#16213e` | Card / panel background |
| `--card-border` | `transparent` | `#0f3460` | Card borders |
| `--table-header-bg` | `#f8f9fa` | `#0f3460` | Table header row |
| `--table-border` | `#eee` | `#1a1a2e` | Table borders |
| `--input-bg` | `white` | `#1a1a2e` | Form inputs |
| `--input-border` | `#ddd` | `#0f3460` | Input borders |
| `--hover-bg` | `#f5f5f5` | `#0f3460` | Hover states |
| `--link-color` | `#4f46e5` | `#93c5fd` | Content links (introduced 2026-07-23) |
| `--link-hover-color` | `#4338ca` | `#bfdbfe` | Link hover |
| `--text-secondary` | `#6b7280` | `#9ca3af` | Muted text |
| `--bar-bg` | `#e5e7eb` | `#3a3a4a` | Progress/stat bar backgrounds |

Common dark-mode pitfalls found across templates:

1. **Hardcoded `#e5e7eb` / `rgba(255,255,255,0.1)`** in stat bars and charts can wash out or disappear in dark mode. Prefer `var(--bar-bg)`.
2. **Hardcoded `#888` / `#666` text** on dark backgrounds fails contrast. Use `var(--text-secondary)`.
3. **Default browser link color (`#0000ee`)** in wiki/markdown content is illegible on dark backgrounds. Wiki now explicitly uses `var(--link-color)`.
4. **Chart.js defaults** (tooltips, grid lines, legend) inherit light colors; pages with charts should set `color`, `grid.color`, and tooltip background/body colors from CSS variables when possible.
5. **Inline `style="background: #f8f9fa"`** in description boxes and modals must have `[data-theme="dark"]` overrides or use `var(--desc-box-bg)`.


The core matching problem: free-text listing titles such as *"MSI GeForce RTX 3060 Ventus 2X 12GB OC"* must map to a canonical reference row.

General approach (details vary by scraper):

1. **Normalize** – lowercase, remove punctuation, expand abbreviations (`8Гб` → `8gb`).
2. **Extract vendor** – look for NVIDIA/AMD/Intel/ASUS/Gigabyte/MSI/etc.
3. **Extract family + model words** – `rtx`, `gtx`, `radeon`, `arc`, `titan`, `quadro`.
4. **Score candidates** with a combination of:
   - exact normalized-name match,
   - token overlap,
   - VRAM compatibility,
   - suffix matching (`OC`, `Ti`, `Super`, `XT`, `50th Anniversary`).
5. **Pick the best** and store `confidence_score` + `match_method`.

The GPU PassMark linker (`link_gpu_passmark.py`) extends this with `significant_tokens()`, which pulls model words out of concatenated normalized names like `titanrtx` so cards such as **TITAN RTX** correctly link to **GeForce RTX Titan**.

---

## 4. Page-by-Page Analysis

### 4.1 Dashboard (`/`)

- **What it shows:** high-level stats: active listings, categories, unmatched rows, recent price changes.
- **Unique features:**
  - Summary cards per category.
  - Quick links to every listing page.
  - Often the entry point for the project board status.

### 4.2 GPU Listings (`/gpu`)

- **What it shows:** graphics-card listings matched to `gpu_reference`.
- **Columns:** Image, Brand, GPU, VRAM, Year, Price, MSRP, G3D, G2D, Rank, Market Position, Location, Date, Actions.
- **Unique features:**
  - **Performance charts:** Price vs G3D, Avg G3D by Vendor, Value Buckets, and Price per G3D Point.
  - **PassMark integration:** `g3d_mark`, `g2d_rank`, and `g2d_mark` pulled from `gpu_reference_passmark`.
  - **Vendor badge** in the Brand column (NVIDIA green, AMD red, Intel blue).
  - **"GeForce" toggle** in filters to hide/show the NVIDIA prefix in GPU names.
  - **NEW / STEAL / UNICORN** image-overlay badges (FIRST and BUY deprecated 2026-07-24).

### 4.3 CPU Listings (`/cpu`)

- **What it shows:** CPU listings matched to `cpu_reference`.
- **Columns:** Image, Brand, CPU, Cores/Threads, Clock, Price, MSRP, Market Position, Location, Date, Actions.
- **Unique features:**
  - Same NEW/STEAL/UNICORN badge overlay logic as the GPU page (FIRST and BUY deprecated 2026-07-24).
  - `discovered_cpu_models` localStorage key is deprecated with FIRST badge and will be removed during `ss_settings_v1` migration.

### 4.4 Computers (`/computers`)

- **What it shows:** Pre-built desktop and laptop listings.
- **Unique features:**
  - Often multi-component listings; matching focuses on brand + title keywords.
  - Uses the shared detail modal and flagging.
  - **Prebuilt / Custom badge** (see Section 4.4.1 below).
  - **NEW / STEAL / BUY deal badges** overlaid on listing images (added 2026-07-29).

#### 4.4.1 Prebuilt vs. Custom classification

Two fields in `computer_listings` drive the badge:

| Field | Type | Purpose |
|-------|------|---------|
| `build_type` | `custom`, `prebuilt`, `office`, `unknown` | Canonical classification. |
| `is_prebuilt` | `boolean` | Cached convenience flag (`build_type == 'prebuilt'`). |

**Badge precedence on the Computers page:**

1. The backend `/api/computers` normalizes each row:
   - `build_type` is forced to one of `custom`/`prebuilt`/`office`/`unknown`.
   - `is_prebuilt` is set to `True` when `build_type == 'prebuilt'`.
   - `pc_type` mirrors `build_type` for the UI filter dropdown.
2. The table row uses `item.is_prebuilt` to decide the badge:
   - `🏭 Prebuilt` (red) when `is_prebuilt === true`.
   - `🛠️ Custom` (green) otherwise.
3. The detail modal (`buildListingInfo`) reads `listing.build_type` directly and also exposes a toggle + admin dropdown to change the type. Changes are persisted via `POST /api/update-listing-type`, which updates both `build_type` and `is_prebuilt` in the database.

**Scraper classification (`SS-CRAWLER/src/scraper/computer_scraper.py:_classify_build_type`):**

1. Buying ads (`pērk`, `покупаю`, `buying`) → `custom`.
2. Part-out markers (`tikai`/`only`/`только ...`/`pārdodu atsevišķi`) → `custom`.
3. Strong prebuilt intent (`gatavs dators`, `gaming pc`, `системный блок`, `pilnībā gatavs`, etc.) → `prebuilt`.
4. Count **core components**: CPU, GPU, RAM, storage, motherboard, PSU, case.
   - 4+ core components → `prebuilt` (full system described).
   - 2–3 core components + weak cue (`dators`, `pc`, `компьютер`, `komplekts`) → `prebuilt`.
   - Otherwise → `custom`.

**Historical inconsistency:**
Earlier versions scored prebuilt keywords against component keywords. A generic title such as *"Datori un orgtehnika/Datori/ Pārdod"* plus a description listing CPU, GPU, RAM and HDD produced a higher component score, so complete PCs were incorrectly labelled `custom`. The classifier was switched to a core-component-count model on 2026-07-29, and existing rows were backfilled. As a result, the 2026-07-28 import went from 65 `custom` / 0 `prebuilt` to 47 `prebuilt` / 18 `custom`.

**Still-classified-as-custom cases are usually legitimate:**
- Buying / part-out ads.
- Server listings missing storage (`bez datu nesējiem`).
- Single-component or barebones listings.

**Files involved:**
- `SS-CRAWLER/src/scraper/computer_scraper.py` — classifier.
- `SS-WEBSITE/app.py` — `/api/computers` normalization, `/api/update-listing-type` persistence.
- `SS-WEBSITE/templates/computers.html` — badge rendering and admin controls.

### 4.5 Laptops (`/laptops`)

- **What it shows:** Laptop listings matched to a per-model reference table.
- **Unique features:**
  - **Per-model reference table** (`laptop_reference`): one row per `brand|model|display_size`, keyed by a case-insensitive `normalized_key` so a single edit propagates to every listing of the same model. Carries `material` (`Plastic` / `Metal`), `usb_c_count`, `usb_count`, `hdmi_count`, `resolution`, and an admin-only `is_valid` (`VALID`) mark.
  - **Real FK link** (`laptop_listings.laptop_reference_id`): the link is now an indexed INT column populated by the scraper, not a soft join on a computed expression. Migration `migrations/2026-08-14_add_laptop_reference_fk.sql` backfilled 771 of 790 existing listings; the remaining 19 are NULL because their `brand` or `model` is NULL. `/api/laptops` and `/api/listing-details/<id>` `LEFT JOIN laptop_reference lr ON lr.id = l.laptop_reference_id`.
  - **Detail popup spec chips** (Material, USB-C / USB / HDMI count, Resolution) pull from the reference table.
  - **✓ VALID badge** on the card title and popup header when the admin has marked the model canonical; the future model-merge job can use this as the target when collapsing near-duplicate laptop models (e.g. `"Macbook Air"` vs `"Macbook air 13"`).
  - **Staff edit panel** in the popup: mod/admin can set material/port counts/resolution; admin can additionally toggle the `VALID` mark. Save is `POST /api/laptop-reference/save`, gated by `require_login + require_role('mod')`; `is_valid` is admin-only and silently ignored for mods.
  - **Resolution pre-fill**: when the table is populated, the most common `\d{3,4}×\d{3,4}` pattern in each model's listing descriptions is stored as the default resolution; staff can correct it.

#### 4.5.1 Laptop reference resolver & matching tolerances

The link between a scraped listing and its `laptop_reference` row is built by `src/scraper/laptop_reference_resolver.py` (Python) and the same rules reproduced in the migration SQL. The tolerances are intentionally conservative — only safe normalizations, no fuzzy matching, because false merges are worse than the extra duplicates.

**Tolerances applied (in order):**

1. **`brand`** — `lower(trim(brand))` with whitespace collapse. `"Apple"` == `"apple"` == `" APPLE "`.
2. **`display_size`** — keep digits and a single optional dot; strip inch marks, `"inch"`, `"collas"`. We do **not** strip trailing `.0` so the key matches the existing rows from the original migration.
3. **`model`** — `lower(trim(model))` + collapse whitespace, then:
   - strip parenthetical content: `"Macbook Pro (2019)"` → `"macbook pro"`
   - strip leading/trailing **Latvian ad-words** (`klēpjdators`, `portatīvais`, `dators`) iteratively so `"Portatīvais dators Lenovo ThinkPad"` → `"lenovo thinkpad"`. English ad-words (`gaming`, `notebook`, `laptop`) are **not** stripped because they appear inside real product names (TUF Gaming A15, Envy Notebook, Surface Laptop).
   - **do not** strip model-name tokens like `M2`, `Pro`, `Air`, `i5`, `X1`, `840`, `14`.
   - **do not** fuzzy-match typos (e.g. `"Macbook"` vs `"Macbok"` stays split — admin merges later via `is_valid`).
   - **do not** strip trailing numbers that happen to equal the display size. Many real model names contain the size (`XPS 13`, `Cyborg 15`, `Vivobook Go 15`, `Macbook Pro 14 M2`); stripping them caused 43 false merges in the test dataset.

The Python module has a doctest-style test suite (`tests/test_laptop_reference_resolver.py`, 11 tests) that pins these rules.

**Scraper flow** (`LaptopScraper._save_listing`):

1. Compute `normalized_key = lower(brand)|lower(model)|display_size_digits`.
2. If `laptop_reference.normalized_key = :k` exists → reuse that `id`.
3. Else **INSERT a new row** with `material=NULL`, port counts `NULL`, and `resolution` auto-extracted from the first `\d{3,4}[x×]\d{3,4}` match in the description. `is_valid=false`; admin must mark.
4. Write `laptop_reference_id` on `laptop_listings` (INSERT and UPDATE paths).

**Backfill for existing data**: the migration `migrations/2026-08-14_add_laptop_reference_fk.sql` (a) re-derives `normalized_key` for every `laptop_reference` row using the same rules, (b) collapses duplicates by picking the lowest-`id` winner and re-pointing any `laptop_listings` to it, (c) backfills `laptop_listings.laptop_reference_id` for all rows whose brand/model are non-NULL. After running: 771 of 790 listings have an FK; refs went from 626 to 624 (2 collapsed via the Dell XPS 13 dedup).

**Resolution backfill**: `backfill_laptop_reference_resolution.py` (in `SS-CRAWLER/`) walks NULL `resolution` rows and re-runs the regex group-frequency check. Run with `--dry-run` first. In practice only ~185 of 624 refs have a resolvable pattern in any of their listings' descriptions — the rest are staff-fillable via the popup UI.

#### 4.5.2 CPU reference resolver & matching tolerances

`laptop_listings.cpu_raw` is a free-text field that the ss.com UI lets sellers fill with whatever they want, and what they fill is messy: `"Intel Core i7-11400H"`, `"I7-11400h"`, `"I7 11400H"` (space instead of dash), `"Inter Core i5"` (typo), `"Intel(R) Core(TM) i7-11400H"`, `"I5-1135g7"`, sometimes a truncated `"Pentium Silve"`. The same physical CPU appears under 3-5 different raw strings, which makes the filter popup messy and the spec popup inconsistent.

To fix that, a second small reference table — `laptop_reference_cpu` — stores the **canonical model** (e.g. `i7-11400H`, `Ryzen 7 5800H`, `M2 Pro`) and the listing carries an FK (`laptop_listings.cpu_reference_id`) that points at it. The scraper uses `src/scraper/cpu_reference_resolver.py` to canonicalize on insert/update; a separate Python backfill re-runs the same rules on existing rows.

**Canonical form** (matches Intel / AMD / Apple / Qualcomm conventions):

- **Intel**: `i7-11400H`, `i5-1135G7`, `i9-13900HX`, `Pentium Gold 7505`, `Celeron N4020`, `Atom N455`
- **AMD**: `Ryzen 7 5800H`, `Ryzen 5 5500U`, `Ryzen 7 Pro 4750U`
- **Apple**: `M1`, `M2`, `M2 Pro`, `M2 Max`, `M3 Ultra`
- **Qualcomm**: `Snapdragon X Elite`, `Snapdragon 8cx Gen 3`

**Tolerances applied (in `normalize_cpu_name`):**

1. Drop `(R)`, `(TM)`, `(®)`, `(™)` marks → space.
2. Drop the trailing `" Processor"`, `" Series"`, `" CPU"`, `" Chip"` words.
3. Drop the trailing clock-speed suffix (`@ 2.40GHz`).
4. Drop the trailing screen size **only when the rest of the model is a 4+ digit SKU** (so `i5-1135G7 14` → `i5-1135G7` but `Pentium Gold 7505` stays whole — we can't tell a 1-digit screen size from a 1-digit class number).
5. Strip brand prefixes (in priority order, case-insensitive): `Intel(R) Core(TM)`, `Intel Core`, `Intel(R)`, `Intel`, `Inter` (common ss.com typo), `core ` (bare `Core i5`), `AMD`, `Apple Silicon`, `Apple`, `Qualcomm`.
6. Canonicalize per vendor:
   - **Intel**: lowercase class letter (`i7`), then the digits, then the suffix **uppercased** (`G7`, `HX`, `G7E`, or empty for desktop parts like `i5-7200`).
   - **AMD**: capitalize `Ryzen`, keep digits, uppercase the suffix letter.
   - **Apple**: capitalize `M`, capitalize Pro/Max/Ultra.
   - **Qualcomm**: capitalize `Snapdragon`, normalize `Gen N`.
7. **Empty / noise inputs** (`""`, `None`, `"Intel"`, `"Processor"`, `"CPU"`, `"@"`) return `(None, "", "")` and the FK stays NULL.

**DB layout** (migration `migrations/2026-08-15_add_laptop_reference_cpu.sql`):

```sql
CREATE TABLE laptop_reference_cpu (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(64) NOT NULL,                    -- Intel / AMD / Apple / Qualcomm
    model VARCHAR(128) NOT NULL,                   -- canonical: 'i7-11400H', 'Ryzen 7 5800H', 'M2'
    normalized_key VARCHAR(256) NOT NULL UNIQUE,   -- lower(brand) | lower(model)
    created_at / updated_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE laptop_listings ADD COLUMN cpu_reference_id INTEGER;
CREATE INDEX ... ON laptop_listings (cpu_reference_id) WHERE cpu_reference_id IS NOT NULL;
```

**Scraper flow** (`LaptopScraper._save_listing`): right after the existing `LaptopReferenceResolver.resolve(...)` call, also call `CPUReferenceResolver.resolve(listing['cpu_raw'], listing['description'])` and write the returned `cpu_reference_id` on both INSERT and UPDATE paths. The resolver UPSERTs on `normalized_key`, so concurrent calls are safe.

**Backfill for existing data**: `backfill_laptop_reference_cpu.py` (in `SS-CRAWLER/`) walks every `laptop_listings` row with non-empty `cpu_raw`, normalizes it, UPSERTs a row into `laptop_reference_cpu`, and updates the listing's FK. Skips rows where the brand is empty (so the `NOT NULL` constraint is never violated). Run with `--dry-run` first. After running the first time: 229 unique reference rows, 659 of 790 listings got an FK; the remaining 131 are listings with NULL `cpu_raw` (21) or un-parseable text like `"Pentium Silve"`, `"Intel core 2"`, `"N3350"`, `"I5 7200U"` (space instead of dash), `"Rayzen 3"` (typo) — admin can fix these later by editing `cpu_raw` and re-running the scraper.

**Spec window & filter popup**: `/api/laptops` and `/api/listing-details/<id>` `LEFT JOIN laptop_reference_cpu` and return `cpu_brand_normalized`, `cpu_model_normalized`, `cpu_ref_id`. A small `getDisplayCpu(item)` helper in `templates/laptops.html` prefers `"${brand} ${model}"` (or just `model` for Apple) and falls back to `cpu_raw`. The CPU filter popup groups listings by the canonical name, so the user sees `"i7-11400H"` once instead of 5 raw variants. The spec window displays the canonical name; admins can later override the display name on the reference row (e.g. add a `display_name` column) if a particular model needs a friendlier string.

**Test coverage**: `tests/test_cpu_reference_resolver.py` has 7 test functions pinning the rules above, including real-data examples like `I5-1135g7 → i5-1135G7`, `i9-13900hx → i9-13900HX`, `AMD Ryzen 7 PRO 4750U → Ryzen 7 Pro 4750U`, `Apple Silicon M2 → M2`, `Snapdragon X Elite → Snapdragon X Elite`, plus rejection cases (`""`, `None`, `"Intel"`, `"Processor"`, `"CPU"`, `"@"`, `"Series"`).

### 4.6 Motherboards (`/motherboards`)

- **What it shows:** Motherboard listings matched to `motherboard_reference`.
- **Unique features:**
  - Filters for socket/chipset/form factor when the scraper extracts them.
  - Badges rendered as table cells rather than image overlays.

### 4.7 Monitors (`/monitors`)

- **What it shows:** Monitor listings with size, resolution, refresh rate, panel type.
- **Unique features:**
  - **Tier calculator** in the detail modal (BEAST/GAMING/EDITORS/MID/LOW) based on size, resolution, refresh rate, and panel type.
  - Tier score stored/calculated on the fly and shown in the modal.

### 4.8 RAM (`/ram`)

- **What it shows:** Memory modules matched to `ram_reference`.
- **Unique features:**
  - RAM listings were once mostly inactive, so price stats fall back to **all unflagged matched RAM of the same type/capacity**, not just active rows.
  - Filters by capacity, type (DDR4/DDR5), speed.

### 4.9 Lenses (`/lenses`)

- **What it shows:** Camera lens listings matched to `lens_reference`.
- **Unique features:**
  - Fuzzy normalized matching for brand, mount, focal length, and aperture in Python.
  - Mount filter is exact case-insensitive (previously `'E'` incorrectly matched `'EF'` / `'EF-S'`).
  - 120 lens listings had to be reactivated after the 7-day stale-deactivation logic turned them off.

### 4.10 SSDs (`/ssd`)

- **What it shows:** SSD listings matched to `ssd_reference`.
- **Unique features:**
  - Capacity and interface filters.
  - Uses shared badge/stats pipeline.

### 4.11 PSUs (`/psu`)

- **What it shows:** Power supply listings matched to `psu_reference`.
- **Unique features:**
  - NEW and STEAL badges overlaid on listing images (added 2026-07-23).
  - Wattage and efficiency filters.

### 4.12 Cases (`/cases`)

- **What it shows:** PC case listings matched to `case_reference`.
- **Unique features:**
  - NEW and STEAL badges overlaid on listing images (added 2026-07-23).
  - Form-factor filters.

### 4.13 Consoles (`/consoles`)

- **What it shows:** Gaming console listings matched to `console_reference`.
- **Unique features:**
  - Shared listing table + modal.
  - Model-level price stats.

### 4.14 PC Builder (`/pc-builder`)

- **What it shows:** A build-planning interface that combines listings from multiple categories.
- **Unique features:**
  - Lets users pick components from scraped listings.
  - Totals the build price.

### 4.15 Models (`/models`)

- **What it shows:** Aggregated statistics per canonical model (GPU, CPU, etc.).
- **Unique features:**
  - Model-level view distinct from the per-listing pages.
  - Price history per model.

### 4.16 Admin (`/admin`)

- **What it shows:** Administrative tools and raw data inspection.
- **Unique features:**
  - Toggleable badges for `listing_id`, `matched_gpu_id`, `matched_cpu_id` in the detail modal.
  - Often used for debugging matches and stale listings.

### 4.17 Project Board (`/project-board`)

- **What it shows:** Kanban-style task board for bugs, features, and scraper maintenance.
- **Columns:** problems → assignment → progress → talking (review) → solved → future.
- **Unique features:**
  - Reopened tasks get highest priority.
  - Per-reopen fix tracking: each `reopen_history` entry has its own `fix` text.
  - Detail modal shows a chronological timeline of initial completion → reopens → fixes.
  - Tasks can be linked to future folders for organized storage of solved work.
  - `board_logger.py` writes a human-readable log of every create/move/reopen/solve event.

### 4.18 Wiki (`/wiki`)

- **What it shows:** This page.
- **Unique features:**
  - Rendered from `docs/project_wiki.md` using Python-Markdown with `toc`, `tables`, and `fenced_code` extensions.
  - Sidebar navigation is auto-generated from headings.
  - Download button for the raw Markdown file.

---

## 5. GPU PassMark Linking Deep Dive

File: `SS-CRAWLER/link_gpu_passmark.py`

Goal: attach PassMark G3D/G2D scores to `gpu_reference` rows so the dashboard can chart price vs performance.

### Match hierarchy

1. `exact_name` – normalized model strings match exactly.
2. `strong_name` – high token overlap + suffix/VRAM compatibility.
3. Family/suffix/token scoring – for cards within the same family (`RTX 30`, `RX 6000`, etc.).
4. VRAM fallback – if a card has the same family and VRAM but the model name is ambiguous.
5. `significant_tokens()` – extracts model words (`titan`, `rtx`, `gtx`) from concatenated normalized strings, fixing cases like `titanrtx` → `GeForce RTX Titan`.

### Output table

`gpu_reference_passmark` stores:

- `gpu_reference_id`
- `g3d_mark`
- `g2d_mark`
- `match_method`

### GPU Page Chart Pipeline

```
gpu_reference_passmark
        ↓
listings (matched, unflagged)
        ↓
/api/gpu-performance-stats  (CTEs compute avg/min/max price, price_per_g3d)
        ↓
Chart.js on /gpu
```

---

## 6. Recent Change Log

### 2026-08-17
- **Cases page: full rebuild to GPU-parity.** `/cases` was barebones — the table never showed data and the detail modal never opened. Three root causes fixed: (1) all 28 case listings were `is_active = false` because no case-scraper has run recently, so the "Active only" default-on filter hid everything; (2) the `/api/cases` query had a `float - Decimal` type bug in the price-stats calculation that returned 500 the moment any row was loaded (this is why the popup never opened); (3) there was only one flat API endpoint — no stats, no per-listing confidence, no rich detail. Added three new endpoints: `/api/case-stats` (totals, by type, by color, by side-panel, by manufacturer, by location, price distribution buckets, confidence tiers), `/api/case-filters` (dropdown values), and `/api/case-reference/<id>` (full reference + related listings). Rewrote `/api/cases` to support all the new filters plus price-history. Page rebuild (`templates/cases.html`): 4 stat cards on top, 3 charts row (price distribution bar chart with FIXED 220px height wrapper to stop it growing to infinity, "By Type" bars, "By Manufacturer" bars), a filter bar with type/color/side-panel/manufacturer dropdowns + min/max price + search + sort/order, a rich listings table with image, name + confidence badge, manufacturer/type/color/side-panel badges, price + avg/percentile, location, first-seen, actions. Detail modal: image, price block with avg/percentile, full case-reference metadata, listing metadata, price history, action buttons (view on ss.com / flag / copy URL). Initial render shows 28 rows (all 28 cases), the price chart's Y-axis now caps correctly at 0-9 instead of growing unbounded.
- **Cases page: Active filter is back as a 3-state select.** Per maintainer: keeping the button is correct because the filter will be meaningful the moment a fresh scrape session runs and the 7-day sweep has data to work with. The Cases page's `Active` filter is now a select (not a checkbox) with three states — `Active only` (default), `Inactive only`, `All` — wired into both the UI (`templates/cases.html`) and the `/api/cases` endpoint (`app.py::get_cases`). A short notice banner above the filter bar now explains the time-based semantics honestly (a 6-day-old listing stays "active" until the next scrape misses it) and points at wiki §7 for the session-bound fix recipe. (Other pages — GPU/CPU/SSD/RAM/Computers/Monitors/Motherboards/Cameras/Lenses/PSUs/Consoles — keep their default-on "Active only" behavior because their scrapers run frequently and the time-based sweep is working as intended there.)
- **Cases Type Guide "Compare at the same scale" — full rebuild (v3).** Maintainer rejected the original v1 family-grouped bars (each row had its own scale — 600mm tower looked the same height as a 150mm desktop, so size differences weren't visible) and asked for a true overlay where all 17 case types are drawn at one scale on a shared baseline. v3 (`templates/case_guide.html` lines 458-650, `/cases/guide`): a single SVG canvas (820×540) with 17 silhouettes, all centered at the same x, all on the baseline y=480, all drawn at 0.62 px/mm. Drawn largest-first to smallest-last (back-to-front) so smaller cases sit on top of larger ones. Each silhouette gets a colored number badge at the TOP (1-17) with a white halo filter (`#numHalo`) so the number stays visible against any case color. The y-axis runs 0-600mm with gridlines every 100mm so users can read exact heights off the canvas. Two reference markers: "1U = 44.45mm" in the right margin (small dashed line at the standard rack-unit height) and an "ATX motherboard 305×244mm" outline in the top-right corner. The legend below is grouped by family (Towers 6 / Desktops 5 / Test benches 2 / Rackmounts 4) with each item clickable — hover temporarily highlights the corresponding silhouette on the canvas (dim others to fill-opacity 0.06, brighten the hovered one to 0.55 with a 3px stroke and a drop-shadow), click pins the highlight until clicked again or the user clicks outside. The CSS-only color key at the bottom shows the family swatches + reference symbols. (Implementation note: the ATX-mobo reference is shrunk to 45% of true scale and parked in the top-right so it doesn't intersect the case stack; the v2 attempt left it at full size in the canvas center where it overlapped the silhouettes.)
- **Cases Type Guide "Compare side profiles at the same scale" — added v3.1.** After v3, maintainer said: *"Compare at the same scale is great, but make it another one comparing from the side"*. Added a second section right below the front-view section, same 0.62 px/mm scale but using H × D (height × depth) dimensions instead of W × H. Center X shifted right to 320 to accommodate the wider depth range (max 550mm Full Tower vs max 482mm rackmount width). New reference markers added: "280 mm typical GPU length" as a vertical dashed line on the right (orange, to distinguish from the 1U marker) and "19" rack = 482.6 mm" as a horizontal dashed line at the top. Side view reveals what the front hides — that towers are tall *and* deep (ATX Full Tower is 600×550, almost square), desktops are wider than tall (true desktop form factor, ATX Desktop 150×430), and rackmounts are uniformly 500 mm deep regardless of height (5U, 4U, 3U, 2U all line up vertically in the silhouette when overlaid — the rack rail standard at work). The hover JS was rewritten to iterate over both `.size-compare` sections and use per-section pinned state, so hovering on a case in the front view doesn't dim the side view and vice versa. (Implementation note: the GPU-length reference uses an orange stroke `#d97706` so it stands out from the gray 1U and 19" markers; the dashed pattern is the same so they read as a coherent reference group.)
- **Listing "Active" logic — review + wiki note (corrected).** Reviewed how `listings.is_active` is set across all scrapers (GPU, CPU, SSD, RAM, Computer, Console, Case, Monitor, Motherboard, Camera, Lens, PSU). There **is** automatic deactivation today — it is **time-based**, not session-based, and is implemented in `SS-CRAWLER/src/database/repository.py::ListingRepository.mark_stale(session, days=N)`. The function runs `UPDATE listings SET is_active = false WHERE last_seen_at < (NOW() - INTERVAL N days) AND is_active = true` and is called at the end of every scrape run from `src/scraper/engine.py:247` and `src/scraper/cpu_scraper.py:236` with `days=self.config.scraper.stale_after_days` (default 7). There are also three other places that flip `is_active = false` on purpose: admin "ignore" action in `SS-WEBSITE/app.py:2627-2632` (unmatched review), `SS-WEBSITE/deduplicate_listings.py:56-60` (dedup), and `SS-CRAWLER/duplicate_prevention_v2.py:67-71` (when content changes for the same `listing_id`). **The time-based sweep has three concrete problems** that match what surfaced on the Cases page: (1) if a scraper is paused for a week every previously-active listing gets wiped even though nothing changed; (2) the cutoff is "from now" not "from the last session boundary", so a daily scrape at 02:00 that finds 0 listings will still mark yesterday's 02:00 sightings as stale; (3) there's no record of when each listing was deactivated, so a seller dispute ("you said my listing was up at 14:00") can't be answered. **Intended contract (per maintainer):** a listing is active iff it was seen in the most recent scrape session for its category. Between sessions, status persists. After a session completes, anything that wasn't re-seen becomes inactive. **Proposed change (see Section 7 for the recipe):** introduce a `scrape_sessions(category, source, started_at, finished_at, listings_seen, listings_new, listings_updated, status)` log table, record `started_at` at the beginning of each category scrape, and replace the time-based `mark_stale` call with a session-bound sweep: `UPDATE listings SET is_active = false, deactivated_at = $finished_at WHERE category = $cat AND is_active = true AND last_seen_at < $started_at` plus add a `deactivated_at` audit column. Frontend implications: the "Active" filter on every page keeps its default-on behavior; the "Uncheck Active" option to see historical rows is the right escape hatch for the transition window.

### 2026-08-15
- **Laptops: canonical CPU reference table (`laptop_reference_cpu`).** `laptop_listings.cpu_raw` is messy (the same i7-11400H appears as `Intel Core i7-11400H`, `I7-11400h`, `I7 11400H`, `Inter Core i7-11400H`, etc.), so a second small reference table — `laptop_reference_cpu` — stores the **canonical model** (`i7-11400H`, `Ryzen 7 5800H`, `M2 Pro`) and the listing carries a real FK (`cpu_reference_id`). New migration `migrations/2026-08-15_add_laptop_reference_cpu.sql` creates the table + the FK column. `src/scraper/cpu_reference_resolver.py` (with 7 unit tests in `tests/test_cpu_reference_resolver.py`) normalizes on the scraper side; `backfill_laptop_reference_cpu.py` re-runs the same rules over existing rows (UPSERT on `normalized_key`). After first backfill: 229 unique reference rows, 659/790 listings linked, 131 NULL (NULL brand/model or genuinely un-parseable text like `"Pentium Silve"`, `"Intel core 2"`, `"N3350"`). `/api/laptops` and `/api/listing-details/<id>` LEFT JOIN `laptop_reference_cpu` and return `cpu_brand_normalized` / `cpu_model_normalized` / `cpu_ref_id`. A small `getDisplayCpu(item)` helper in `templates/laptops.html` shows the canonical name in the card, the spec window, and the filter popup — so the popup groups `"i7-11400H"` once instead of 5 raw variants. Scraper is wired (`LaptopScraper._save_listing` resolves the CPU FK on every INSERT and UPDATE). Schema for fresh installs updated in `src/database/schema_laptops.sql`. New wiki section 4.5.2 documents the canonical forms, tolerances, and backfill.
- **Laptops: CPU filter popup toggles replace checkboxes.** Removed the visible `<input type="checkbox">` from the CPU filter rows; the whole row is now the toggle target with a 3px colored left border on selection, an animated check icon, and a colored count badge. `Select all` is a pill button that goes from outlined → filled when all are checked. No fake checkbox. Fully keyboard-accessible (the underlying input is still focusable; CSS handles the visual state via `:has(input:checked)`).
- **RAM page UI redesign.** `templates/ram.html` got a full visual overhaul — no more browser-default checkboxes, no more 4-color action pills. Replaced the toggle bar with three pill buttons (Active only / High conf ≥70% / All RAM avgs) using the `.on`/`.active` class pattern. Action buttons collapsed from 4 differently-colored pills (History/Info/Flag/View) into 4 icon-only 28×28 squares with a single primary hover color and a red hover for flag. Stat cards redesigned: top row of 4 cards (DDR4 active market, DDR3, DDR5, Total) with a 3px colored left accent bar, glow dot, and a thin progress bar; DDR3 red, DDR4 blue, DDR5 purple. Below: a 5-column capacity mini-grid (4 GB → 64 GB+) with per-DDR counts and colored dots — clicking a capacity card sets the Capacity filter and reloads. Then the two charts (Avg Price by DDR Type as dual-axis line, Capacity Distribution as donut). The Top Deals strip auto-hides when no deals. Filter bar uses the same `.filter-chips` pill pattern for DDR (All / DDR3 / DDR4 / DDR5). Cell renderers rebuilt: image cell with 60×60 thumbnail + stacked badges (NEW green, STEAL red, UNICORN gradient), RAM cell with name + DDR chip + capacity chip + speed + slim confidence bar, price cell with large bold price + €/GB + colored "↓ below avg" / "↑ above avg" tag, latency as monospace CL16, model/market position as compact stat blocks with mini progress bars. Summary row uses a colored accent top border. `loadStats()` now also reads `stats.by_ddr` from the API to fill the per-DDR cards; the API (`/api/rams/stats` in `app.py`) was extended with a per-DDR GROUP BY query that returns `{ total, active, avg, median }` per DDR type plus a `total_active` field. New CSS uses CSS variables for theming (works in both light and dark mode). Reference screenshot saved to `docs/ram_page_redesign_preview.png`. Three backfill scripts (`backfill_ram_ui.py` for CSS, `backfill_ram_ui_v2.py` for content, `backfill_ram_ui_v3.py` for JS) made the change reviewable. Default `useActiveOnly` is now `false` (so all listings show on page load; toggle to filter).
- **Computers page UI redesign.** `templates/computers.html` got the same treatment. Title column was showing the raw SS.COM breadcrumb (e.g. `"Datori un orgtehnika/Datori/ Pārdod prebuilt €100"`) which had the price embedded in the title — added `cleanComputerTitle()` helper that strips the breadcrumb variants (`Datori un orgtehnika/Datori`, `Datori un orgtehnika - Datori, Cena N €`, `Datori un orgtehnika/Datori/Pārdod`) and the trailing `- Sludinājumi` suffix. If the cleaned title is empty (e.g. the listing was nothing but the breadcrumb), it falls back to `Prebuilt PC` / `Custom PC`. Filter bar replaced the 3 checkboxes (Active only, Prebuilt only, Hide Prebuilt) with 3 pill toggles that share the same `.on`/`.active` pattern as the RAM page; the admin "Mark Prebuilt Mode" pill is hidden by default (still toggled via `toggleAdminMarkMode()`). Sort/Order merged into one `.filter-group` with a `SORT` label. `loadComputers()` was rewritten to read pill state via `classList.contains('on')` (back-compat: returns `true` for `active-only` if the pill doesn't exist yet). Table header dropped the redundant "Type" column (it was just `prebuilt` / `custom` which now lives next to the title as a small `.pc-type-chip` chip — red for prebuilt, blue for custom). Added a "Score" column showing `⚡ perf` (blue) and `💎 value` (green) as small chips. Components cell rebuilt as a 2-column grid (CPU+GPU top row, RAM+SSD bottom row) with colored tag pills (`.comp-tag.comp-cpu/gpu/ram/ssd`) and `.comp-name` truncated with `text-overflow: ellipsis`. Removed the redundant prebuilt chip from the components column (it was already in the Type column). Price cell now shows big bold price + optional "−€X below parts" green subtitle when `price_difference_eur < 0` (uses `components_total_eur` to show how far under parts the listing is). Date cell uses compact `en-GB` format (`28 Jul`). Action buttons collapsed from 2 colored pills (Details gray, View → purple) into 2 icon-only squares (📄 details, ↗ open) with single primary hover. CSS uses the same CSS variables pattern as RAM. `backfill_computers_ui.py` was created but failed to apply due to file truncation; reverted from git and applied the changes directly with `edit` for safety. Also fixed a pre-existing JS bug where `/\//thumb\//` (the `/thumb/` URL path replacement) was being parsed as a regex literal followed by a comment, breaking the entire script. Fixed in 3 places (loadComputers, showComputerDetail, showImageModal). Reference screenshot saved to `docs/computers_page_redesign_preview.png`.

### 2026-08-14
- **Laptops: shared per-model reference table (`laptop_reference`).** New table keyed by a case-insensitive `brand|model|display_size` `normalized_key` so a single edit propagates to every listing of the same model. Migration at `migrations/create_laptop_reference_table.sql` created the table and pre-populated 626 rows from the 790 in `laptop_listings`; 185 had `resolution` auto-filled by regex (`\d{3,4}×\d{3,4}`) over the listing description. `/api/laptops` and `/api/listing-details/<id>` LEFT JOIN this table, so the card title, detail popup, and edit panel all read the same row. The detail popup shows the reference data as spec chips (Material, USB-C / USB / HDMI count, Resolution); staff (`mod`/`admin`) get a small edit panel, and the `✓ VALID` badge appears on the card title and popup header for admin-marked canonical models. Saving the reference is `POST /api/laptop-reference/save`, gated by `require_login + require_role('mod')`; the `is_valid` field is admin-only and silently ignored for mods so the gate cannot be bypassed from the client. Future merge work (T286) can use `is_valid=true` as the canonical target when collapsing near-duplicate laptop models (e.g. `"Macbook Air"` vs `"Macbook air 13"` with a redundant `display_size`).
- **Laptop detail popup: image lightbox wired up:** the popup image in `templates/laptops.html` now opens the full-size lightbox (`.lightbox-overlay`, darkened backdrop) on click. The CSS and `openLaptopLightbox()` existed but were never attached to the popup image. Also added Escape-to-close in the capture phase with `stopPropagation()` so Escape closes only the lightbox, not the underlying modal (base.html has a global modal Escape handler).
- **Laptop detail popup: compact spec chips:** replaced the full-width `.spec-row` list with a responsive `.spec-grid` of icon chips (`.spec-chip`), scoped to `.laptop-detail-body` in `laptops.html`. Uses theme variables (`--bar-bg`, `--table-border`, `--text-secondary`) so dark mode works. Also fixed `Display` rendering `13""` when `display_size` already contained an inch mark, and capitalized `seller_type`.
- **Laptop filters: toggle chips replace checkboxes:** the five filter checkboxes (`macbook-only`, `active-only`, `exclude-flagged`, `include-perekups`, `include-lombards`) are now pill-shaped `.toggle-chip` labels grouped together at the end of the filter bar, instead of stacked checkbox-above-text labels (base.html `.filters label` is column-flex, which broke the old layout). State is pure CSS via `:has(input:checked)` — no JS changes needed; inputs keep their IDs and stay focusable (`:focus-visible` ring) for keyboard users. `Include macbooks` also moved out from between the CPU and GPU filters.
- **Laptop filters: compact bar layout:** page-scoped override in `laptops.html` makes `.filters label` horizontal (label inline next to control, ~0.8rem font, tighter padding/gaps) instead of base.html's stacked column layout. Min € / Max € merged into one `Price €` group (placeholder-based), and Sort/Order merged into one `Sort` group. Header row margin reduced. Other pages keep the base stacked layout.

### 2026-08-12
- **Shared thumbnail styles (page compatibility fix):** Several listing pages (GPU, CPU, Laptops, RAM, SSD, Monitors, Lenses, Motherboards, Cases, PSU) lost their per-page `.listing-thumb`/`.listing-thumb-placeholder` CSS and displayed broken image thumbnails. Added a shared rule in `templates/base.html` so every page that uses these classes gets consistent sizing (`max-width: 90px; max-height: 70px; object-fit: cover; border-radius: 6px; cursor: pointer`). Pages that already define their own rules (`cameras.html`, `computers.html`) continue to override via `{% block extra_css %}`.
- **Wiki / GPU dashboard left-clustering fix:** CSS Grid `fr` tracks default to `minmax(auto, 1fr)`, so cards with narrow content (loading text, short lists) shrank to their content width and left large empty space on the right. Switched the wiki layout (`templates/wiki.html`) and GPU stats/chart grids (`templates/gpu.html`) to `minmax(0, …fr)` so tracks always fill the available container width.

### 2026-07-24
- **Wiki review resolutions:** maintainer asked separate designer and technical subagents for follow-up recommendations, then recorded binding decisions in `docs/project_wiki.md` Section 14.
  - **Auth model:** flagging/unflagging/delete are admin-only; implement Flask-Login + `/api/me`.
  - **Badge contract:** keep **NEW**, **STEAL**, **UNICORN**; deprecate **FIRST** and **BUY**.
  - **Shared modal:** target architecture is `showSharedListingDetail`; migrate bespoke modals in priority order.
  - **Active/flagged semantics:** two explicit toggles (`active_only`, `exclude_flagged`), both default on.
  - **Settings registry:** centralize under `ss_settings_v1` with migration helper.
  - **Responsive baseline:** desktop-first; card view below 768 px; `prefers-reduced-motion` guard in `base.html`.
- **Implementation tasks:** added `docs/implementation_tasks.md` with 26 copy-pasteable task prompts (T001–T026), grouped into phases P0–P6. Added companion Section 16 in the wiki.
- **Dark-mode fix:** added `--code-bg`/`--code-text` variables and fixed wiki code-block contrast.

### 2026-07-23
- **GPU PassMark linker:** added `significant_tokens()` so `TITAN RTX` links to `GeForce RTX Titan`; 325 PassMark rows matched after re-run.
- **GPU page:** added G3D/G2D/Rank columns, NEW/STEAL/UNICORN image-overlay badges, and four performance/value charts.
- **GPU chart resilience:** fixed infinite-resize bug by wrapping charts in fixed-height `.perf-chart-box`; capped scatter points at 10; disabled animations.
- **Cases / PSUs:** added NEW/STEAL image-overlay badges.
- **Project board:** added per-reopen `fix` field inside `reopen_history[]`; migrated 65 existing tasks.
- **Wiki:** created `/wiki` route, `templates/wiki.html`, sidebar TOC, and this living Markdown document.
- Fixed corrupted project-board task `T203` (missing `title`) and hardened modal against missing fields.
- Documented GPU deal-badge logic in `docs/gpu-tags-analysis.md`.
- Added the same deal badges to the CPU page.
- Fixed `/lenses` by reactivating 120 stale lens listings and correcting mount filter logic.

### 2026-07-18
- CPU-PRICES scraper fixed to crawl all pages instead of `max_pages=1`.
- Cinebench R23/R26 scrapers ready using div-based `cpu-monkey.com` selectors.

### 2026-04-19
- Fixed `/api/gpus` and `/api/cpus` `KeyError` by adding `matched_gpu_id` / `matched_cpu_id` to SELECT.
- Improved RX Vega 56 / RX 570 matching: vendor detection excludes OEM-only brands and VRAM matching is stricter.

---

## 7. Common Pitfalls & How to Avoid Them

| Pitfall | Why it happens | Fix |
|---------|----------------|-----|
| Page shows "No listings found" | Listings deactivated after 7 days without sightings. | Use the Active filter's `All` option (or `Inactive only` to see the deactivated ones), or reactivate rows. |
| `is_active` flips to `false` based on wall-clock time, not per-session visibility — so a paused scraper nukes every listing after 7 days, and a daily 02:00 scrape can mark yesterday's 02:00 sightings stale | `mark_stale()` in `SS-CRAWLER/src/database/repository.py:482-501` uses `last_seen_at < NOW() - INTERVAL N days`, called from `engine.py:247` and `cpu_scraper.py:236`. Has no notion of "session boundary". | **Introduce `scrape_sessions(category, source, started_at, finished_at, listings_seen, listings_new, listings_updated, status)`.** At the start of each per-category scrape, insert a row with `started_at=NOW(), status='running'`. Replace the `mark_stale` call with: `UPDATE listings SET is_active = false, deactivated_at = $finished_at WHERE category = $cat AND is_active = true AND last_seen_at < $started_at` (the session's `started_at`, not NOW()). Then update the session row to `status='done', finished_at=NOW(), listings_seen=...`. Optional: add `deactivated_at TIMESTAMPTZ` column to `listings` for audit. A listing is then "active" iff it was seen in the most recent scrape session for its category — robust against scraper pauses, scraper skips, or partial failures. Frontend "Active" filter stays default-on; "Show all (incl. inactive)" remains as the escape hatch. |
| Price stats missing for a model | Need ≥2 active, unflagged matched listings. | Wait for more listings or check flagged rows. |
| `KeyError: matched_*_id` | API SELECT missing the matched ID column. | Include `l.matched_gpu_id` etc. in queries. |
| Charts grow forever / page lags | Chart.js responsive container has no fixed height. | Use `.perf-chart-box { height: 250px; overflow: hidden; }`. |
| `titanrtx` links to wrong GPU | Concatenated normalized names defeat token overlap. | Use `significant_tokens()` to extract model words. |
| Mount filter `'E'` matches `'EF'` | String `LIKE '%E%'` is too broad. | Use exact case-insensitive comparison after normalization. |
| Emojis show as mojibake | File saved in wrong encoding. | Keep templates UTF-8 and open with `encoding='utf-8'`. |
| Wiki TOC not generated | Markdown not converted with `toc` extension. | Use `markdown.Markdown(extensions=['toc', ...])`. |

---

## 8. How to Run & Develop

```bash
# Dashboard
cd SS-WEBSITE
python app.py          # http://localhost:5000

# Install/update deps
pip install -r requirements.txt

# Scraper / linker work (use the SS-CRAWLER venv)
cd ../SS-CRAWLER
python link_gpu_passmark.py
```

**Before committing:** run `python -m py_compile app.py` and hit the page you changed in a browser. If it has charts, open DevTools and confirm the canvas container height is stable.

---

## 10. Design Review Notes (2026-07-23)

A focused UI/UX review of the dashboard was performed. The questions below are intentionally open — they help decide whether the current design direction is deliberate or accidental. The gaps table records concrete issues and the files that need to change.

### 10.1 Design questions for the maintainer

1. **Color-token completeness**: `:root` and `[data-theme="dark"]` define many variables, but colors like `#667eea`, `#764ba2`, `#27ae60`, `#e74c3c`, `#f39c12`, `#00d4ff`, `#3b82f6`, `#9b59b6`, `#95a5a6`, `#00d4ff` are still hardcoded in dozens of places. Do you intend to allow full theme swapping, or are accent colors intentionally brand-locked?
2. **Navbar responsiveness**: The navbar renders every category link inline on desktop but there is no visible mobile breakpoint or hamburger. Has mobile/tablet navigation been considered, or is this dashboard desktop-only?
3. **Unicorn badge accessibility**: The `.unicorn-badge` uses a fast rainbow animation, glow, float, and shine sweep. Have you tested this for users sensitive to motion? Should there be a `prefers-reduced-motion` fallback?
4. **Column-gear placement**: CPU and RAM pages implement the column rearrange/hide feature differently (CPU: gear inside the Actions header; RAM: gear as an extra column). Should this be unified across category pages, or is the divergence intentional?
5. **Detail modal dark-mode overrides**: `#shared-listing-content` has many `[data-theme="dark"]` hardcoded overrides (`#0f3460`, `#16213e`, etc.). Why not extend the CSS variables to cover modal variants instead of duplicating values?
6. **Chart responsiveness on high-DPI / small screens**: Chart containers have fixed heights, but on narrow viewports the `2fr 1fr 1fr` / `repeat(auto-fit, minmax(400px, 1fr))` grids can overflow. Is there a minimum supported viewport width?
7. **Deal badge semantics**: Badges mix colors (`#16a34a`, `#dc2626`, `#3b82f6`, `#9333ea`) and terms (`STEAL`, `NEW`, `FIRST`, `UNICORN`) across pages. Is there a single source of truth for deal-badge styles, or is per-page customization desired?

### 10.2 Concrete design gaps + status

| # | Gap | File + Recommended fix | Status |
|---|-----|------------------------|--------|
| 1 | **Missing `prefers-reduced-motion` guard** — The unicorn badge and widget drag animations can be distracting or problematic for motion-sensitive users. | `base.html` CSS: add `@media (prefers-reduced-motion: reduce) { .unicorn-badge, .widget-card, .drag-clone { animation: none; transition: none; } }` | ✅ Applied 2026-07-23 |
| 2 | **Hardcoded dark-mode modal colors** — `#shared-listing-content` redeclares the dark palette inline, making future palette updates error-prone. | `base.html`: extend `:root`/`[data-theme="dark"]` with `--modal-highlight-bg`, `--modal-warn-bg`, `--modal-muted-bg`, `--modal-box-bg`, `--modal-border`, then remove the `[data-theme="dark"] #shared-listing-content ... !important` overrides. | ⬜ Pending |
| 3 | **No mobile navbar breakpoint** — The long horizontal nav will wrap awkwardly on tablets and overflow on phones. | `base.html`: add a `@media (max-width: 900px)` rule that collapses `.nav-links` into a hamburger menu, or move overflow categories into a “More ▾” dropdown. | ⬜ Pending |
| 4 | **Inconsistent column-customization UI** — RAM renders the gear in a separate `<th>` while CPU embeds it inside Actions; GPU has none. | `cpu.html` / `ram.html` (and future `gpu.html`): agree on one pattern. Recommendation: embed the gear inside the rightmost “Actions” header so hiding the Actions column still exposes the settings gear (as CPU does), and share one JS/CSS component. | ⬜ Pending |
| 5 | **Filter-bar overflow on narrow screens** — The filters section uses inline labels with `gap: 1rem` and special pill-shaped inputs that can overflow horizontally before wrapping cleanly. | `gpu.html`, `cpu.html`, `ram.html`: add `@media (max-width: 768px) { .filters { flex-direction: column; align-items: stretch; } .filters label { width: 100%; } }` and replace fixed-width inputs with `width: 100%` on small screens. | ⬜ Pending |

---

## 11. Technical Review Notes (2026-07-23)

A page-by-page technical review was run in four focused passes: GPU/CPU/RAM/SSD, Motherboards/Monitors/Cameras/Consoles, Lenses/Cases/PSU/Admin, and Computers. The notes below summarize the cross-page architecture questions and the concrete gaps found in each area. All fixes are recorded as **pending** until they are implemented and verified.

### 11.1 Cross-page architecture questions

1. **What does “active” actually mean?** Some endpoints treat `active` as `is_active = true`; the GPU “Active-only averages” checkbox actually toggles flagged exclusion; RAM’s `use_active_avg` toggles active-only vs all-unflagged. Should “active” and “unflagged” be two separate, explicit toggles everywhere?
2. **Why are chart endpoints inconsistent with listing endpoints?** GPU performance stats exclude flagged but include inactive listings; SSD statistics include flagged active listings; CPU platform stats include flagged listings. Should charts mirror the default active+unflagged view?
3. **Why is the detail modal implementation fragmented?** Monitors use a shared `showSharedListingDetail`; Motherboards, Cameras, Consoles, Lenses, and Computers define bespoke modals; Cases uses `showModal`; PSU references `showSharedListingDetail` but does not define it. Is there a target shared pattern?
4. **Why are there two flag APIs?** `/api/flag` (used in Admin unmatched modal) and `/api/flag-listing` (category pages) accept different payloads (`comment` vs `reason`/`flag_category`). Consoles uses `/api/unflag-listing/<id>` while the backend summary lists `/api/unflag`. Which routes are canonical?
5. **Who is allowed to flag listings?** Flag buttons appear on nearly every page with no visible role or admin gate. Is flagging open to all viewers, or is permission enforced elsewhere?
6. **Why are confidence/match columns category-specific?** `listings` has `confidence_score` (GPU), `cpu_confidence_score`, `ssd_confidence_score`, `ram_confidence_score`, `console_confidence_score`, etc. Is this deliberate denormalization, or should matching scores live in a normalized per-category table?
7. **Where is the localStorage settings registry?** Admin toggles and column-customization keys are scattered across pages. Some keys collide (e.g., `showListingId` is used by GPU, Admin, and Lenses with different defaults). Should there be a single settings module?

### 11.2 Concrete technical gaps + status

| # | Page / Area | Gap | File + Recommended fix | Status |
|---|-------------|-----|------------------------|--------|
| 1 | GPU | **VRAM unit mismatch:** `gpu_reference.vram_gb` stores MB but the name/labels say GB. | `app.py` + `gpu.html` + DB: rename column to `vram_mb` (or migrate to GB), align `format_vram()`, and have the frontend send GB while the API converts to the stored unit. | ⬜ Pending |
| 2 | GPU / SSD / CPU charts | **Chart pipelines include flagged or inactive listings.** GPU perf stats include inactive; SSD stats and CPU platform stats include flagged active listings. | `app.py`: add `NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)` to `/api/gpu-performance-stats`, `/api/ssd-statistics`, `/api/ssd-cost-per-gb-timeline`, `/api/cpus/platform-stats`; for GPU charts also add `l.is_active = true`. | ⬜ Pending |
| 3 | GPU / RAM | **`use_active_avg` name and behavior are misleading.** It toggles flagged exclusion in some routes and active-only in others. | `app.py` + templates: split into explicit `active_only` and `exclude_flagged` parameters; update `get_active_avg_clauses()` and relabel the GPU checkbox. | ⬜ Pending |
| 4 | CPU | **Per-listing model stats include flagged active listings.** Avg/min/max/percentile badges on CPU cards are skewed by flagged rows. | `app.py` `/api/cpus`: add `NOT EXISTS (SELECT 1 FROM flagged_listings fl ...)` to the per-model stats subquery. | ⬜ Pending |
| 5 | RAM | **Market-position stats ignore active/flagged filters.** Percentile/below-average badges compare against all listings. | `app.py` `/api/rams`: in the market-position CTE, add `l.is_active = true` and exclude flagged listings. | ⬜ Pending |
| 6 | Motherboards | **Flagging does not refresh backend-derived charts.** After flagging, the row is removed locally but chipset/socket/model stats stay stale. | `motherboards.html`: in `submitFlag`, call `fetchChipsets(); fetchSocketStats(); fetchModels();` after re-rendering. | ⬜ Pending |
| 7 | Monitors | **Stats/charts ignore the time filter and recompute from listing endpoint.** Category counts, performance stats, and cost charts do not pass `time`. | `monitors.html`: use `/api/monitor-stats?time=${timeFilter}` for distributions and pass `time` to cost-chart data source. | ⬜ Pending |
| 8 | Cameras | **No confidence filter.** Unlike other pages, cameras cannot hide low-confidence matches. | `cameras.html`: add a `min-confidence` select to filters, default `0.7`, and include it in `URLSearchParams`. | ⬜ Pending |
| 9 | Consoles | **Unflag endpoint mismatch.** Consoles posts to `/api/unflag-listing/<id>` while the backend summary lists `/api/unflag`. | `consoles.html`: verify the canonical route and update `toggleFlag`/`toggleFlagWithComment` accordingly. | ⬜ Pending |
| 10 | Lenses | **Active/flagged filtering handled partly in the frontend.** Flagged rows are hidden with `display:none`, skewing counts and summaries. | `app.py` `/api/lenses` + `lenses.html`: exclude flagged listings in SQL by default; remove frontend-only hiding. | ⬜ Pending |
| 11 | Cases | **Deal-badge code is duplicated and never rendered.** `computeCaseDealBadges` is defined twice and its result is not inserted into the table. | `cases.html`: remove duplicate function and either inject the badge into the price cell or delete dead code. | ⬜ Pending |
| 12 | PSU | **N+1 price-history fetch merges data into listing objects.** The grid fetches `/api/price-history/<id>` for every row, risking field overwrites and wasted requests. | `psu.html`: remove the `Promise.all(listings.map(fetch price-history))` block; fetch history only when opening the detail modal. | ⬜ Pending |
| 13 | PSU | **Detail handler is undefined.** `showSharedListingDetail` is referenced but not defined in `psu.html`. | `psu.html`: define a local detail handler or confirm `base.html` exposes it globally. | ⬜ Pending |
| 14 | Admin | **Unmatched matching lacks models for lens/camera/monitor/console.** The category filter includes them but there are no model arrays or mappings. | `admin.html`: fetch models from `/api/lens-models`, `/api/camera-models`, etc., and extend `getCategoryModels`, `formatModelDisplay`, and `getMatchAction`. | ⬜ Pending |
| 15 | Computers | **Variable used before declaration.** `isPrebuilt` is referenced before `const isPrebuilt = ...` in the row renderer. | `computers.html`: move `isPrebuilt`/`pcType` declarations to the top of the `forEach` block. | ⬜ Pending |
| 16 | Computers | **Admin mode split across inconsistent localStorage keys.** `adminPrebuiltToggle` and `adminMode` enable different UI pieces. | `computers.html`: standardize on a single `adminMode` key and make `isAdminMode()` the single source of truth. | ⬜ Pending |
| 17 | Computers | **Component filters are client-side only.** They hide rendered DOM rows and cannot work with server-side pagination. | `computers.html` + `/api/computers`: move filters to query params (`cpu_brand`, `gpu_brand`, `ram_min`, etc.) and apply them in SQL. | ⬜ Pending |
| 18 | Computers | **Stats panel ignores current filters.** `/api/computers/stats` is called with no params while the grid uses `active`/`prebuilt`. | `computers.html`: pass the same query params to `/api/computers/stats`; update the backend to apply them. | ⬜ Pending |
| 19 | Computers | **Flagged listings may not be excluded.** No visible `flagged` filter on `/api/computers` and only a delayed refresh after flagging. | Backend `/api/computers` + `/api/computers/stats`: join against flags and exclude non-resolved flagged rows from default views. | ⬜ Pending |
| 20 | Cross-page | **No page persists the `active-only` checkbox in localStorage.** Users lose the preference on reload and pages default differently. | Add a small helper in `base.html` or per-page to read/write the active-only state under a page-specific key. | ⬜ Pending |

### 11.3 Per-page highlights

#### GPU, CPU, RAM, SSD
- **GPU:** `vram_gb` stores MB; the `use_active_avg` toggle conflates active and unflagged; chart stats include inactive listings.
- **CPU:** per-listing stats are active-only but flagged-inclusive; no `use_active_avg` toggle; CPU class filter is applied in both SQL and JS.
- **RAM:** market-position stats are computed over all listings; top-level `/api/rams/stats` also ignores active/flagged.
- **SSD:** listing endpoint excludes flagged, but chart endpoints (`/api/ssd-statistics`, `/api/ssd-cost-per-gb-timeline`) include flagged active listings.

#### Motherboards, Monitors, Cameras, Consoles
- **Motherboards:** bespoke detail modal; flagging refreshes only the listing grid, not chipset/socket/model charts.
- **Monitors:** uses shared detail modal but recomputes stats client-side from `/api/monitors` without passing the time filter.
- **Cameras:** no `min_confidence` or time filter; bespoke detail modal; stats computed client-side.
- **Consoles:** rich flagging UI and client-side flagged-row exclusion; unflag endpoint may be stale; no localStorage persistence for active-only.

#### Lenses, Cases, PSU, Admin
- **Lenses:** two overlapping match controls (`min_confidence` vs `match_status`); frontend-only flagged-row hiding; `showListingId` key collision.
- **Cases:** duplicated dead deal-badge code; custom modal; no flag/delete actions; no admin toggles.
- **PSU:** N+1 history fetch; `showSharedListingDetail` undefined; wattage-average ignores current filters.
- **Admin:** dual flag APIs (`/api/flag` vs `/api/flag-listing`); CSV export fields may not match API output; no localStorage settings registry.

#### Cross-Review Blind Spots

#### Computers
- Prebuilt detection precedence is now documented in Section 4.4.1; the scraper uses core-component counting rather than keyword scoring, and the page uses `is_prebuilt` as the single source of truth with `build_type` as the persisted canonical value.

---

## 12. Cross-Review Blind Spots (2026-07-23)

After the design and technical reviews were written, both sets of findings were cross-checked for contradictions and gaps. This section captures where the two reviews disagree, what neither side caught, and the decisions that must be made before the next implementation pass.

### 12.1 Contradictions between design and technical findings

| # | Topic | Design view | Technical view | Resolution |
|---|-------|-------------|------------------|------------|
| 1 | **Deal badges** | Asks whether there should be a single source of truth for badge styles/terms. | Finds duplicated, dead, or never-rendered badge logic in cases, computers, PSU, etc. | **Resolved 2026-07-24:** Keep **NEW**, **STEAL**, **UNICORN** everywhere; drop **FIRST** and **BUY**. Build a shared frontend badge component fed by a normalized backend `price_stats` contract. |
| 2 | **Unicorn badge** | Flags motion/accessibility concerns. | Shows the badge is tied to inconsistent percentile/price-stat computations, so it may be mathematically unreliable. | **Resolved 2026-07-24:** Keep UNICORN, but fix the data pipeline first (exclude flagged/inactive from percentile calculations). Add `prefers-reduced-motion` guard in `base.html`. |
| 3 | **Column customization** | Sees a UX inconsistency (CPU gear inside Actions vs RAM gear as extra column). | Notes incompatible localStorage key names and API semantics across pages. | **Resolved 2026-07-24:** Gear always lives in the rightmost “Actions” header. Shared frontend contract (`ss_columns_<page>`) first; optional backend schema endpoint later if justified. |
| 4 | **Active/flagged semantics** | Treats the filter bar as a responsive layout problem. | Finds labels are misleading: GPU “Active-only averages” really means “exclude flagged”; RAM semantics differ; CPU has no toggle. | **Resolved 2026-07-24:** Two explicit toggles everywhere: **“Active listings only”** and **“Exclude flagged listings”**, both default **on**. Rename/remove `use_active_avg`. |
| 5 | **Detail modals** | Recommends refactoring shared-modal dark-mode CSS. | Finds most pages use bespoke modals; PSU references a shared handler that is not defined; monitors is the only page using it. | **Resolved 2026-07-24:** Target architecture is a single shared modal (`showSharedListingDetail`). Migrate bespoke modals in priority order: Motherboards → Computers → Consoles → Lenses → Cameras/Cases. Then refactor CSS variables. |

### 12.2 Blind spots neither review caught

- **Security/permissions:** No review inspected backend auth decorators or session handling. Flag buttons and admin toggles are client-side `localStorage`-gated; it is unclear whether any viewer can flag or delete listings.
- **Concurrency / race conditions:** What happens when two users flag the same listing, when a scraper run changes `is_active` while a page is open, or when a listing is deleted while its detail modal is open?
- **Performance / payload size:** PSU fetches `/api/price-history` for every grid row (N+1); monitors recomputes stats client-side from the full listing endpoint; admin unmatched matching loads large model arrays. No endpoint timing or payload budgets were measured.
- **Empty and error states:** Neither review documented what the UI shows when an endpoint returns `[]`, 500s, or when every listing is flagged.
- **Mobile touch interactions:** Beyond the missing navbar breakpoint, dense tables, drag-to-reorder, and modals have not been assessed for touch targets or small-screen usability.
- **Observability:** No logging, metrics, or error-tracking strategy is described.
- **localStorage migration:** Keys are inconsistent and collide. There is no plan for renaming or versioning settings without stranding users.

### 12.3 Combined follow-up questions — with maintainer resolutions (2026-07-24)

1. **Active/flagged semantics**
   - *Question:* What is the canonical definition of an “active” listing, and should the dashboard expose two separate toggles (`active only` and `exclude flagged`) everywhere?
   - *Resolution:* **Active** = `listings.is_active = true`. **Flagged** = row exists in `flagged_listings`. Two explicit toggles everywhere, both default **on**. Rename/remove `use_active_avg`.

2. **Flagging authorization**
   - *Question:* Is flagging an admin-only action? If so, how is that enforced on the backend?
   - *Resolution:* **Admin-only**. Implement Flask-Login with a single admin role backed by environment variables (`SS_ADMIN_USER`, `SS_ADMIN_PASSWORD_HASH`). Add `@login_required` + `@admin_required` decorators on flag/unflag/delete endpoints. Frontend discovers role via `/api/me` and renders destructive controls only for admins.

3. **Detail modal architecture**
   - *Question:* Which detail-modal pattern is the target architecture: shared (`showSharedListingDetail`) or bespoke per category?
   - *Resolution:* **Single shared modal** is the target. Migration priority: Motherboards → Computers → Consoles → Lenses → Cameras/Cases. Modal becomes full-screen below ~640 px.

4. **Deal badges**
   - *Question:* Should deal badges be a single shared component fed by a normalized backend `price_stats` object, or are category-specific rules intentional?
   - *Resolution:* **Single shared component** fed by a normalized backend `price_stats` contract. Keep **NEW** (first_seen batch), **STEAL** (≥15% below model avg), **UNICORN** (exceptional value percentile). Drop **FIRST** and **BUY**. Colors fixed: NEW = blue, STEAL = green, UNICORN = purple.

5. **Backend pagination / growth**
   - *Question:* How large is the dataset expected to grow, and should filtering/stats move to backend with server-side pagination?
   - *Resolution:* **Deferred.** Move filters/stats to backend with URL params when inventory growth makes client-side filtering unreliable. First step: server-side filtering for Computers (component filters) and pagination for GPU/CPU. Keep current client-side approach for smaller categories until metrics show need.

6. **Viewport and input modality**
   - *Question:* What is the minimum supported viewport and input modality (desktop-only, tablet, phone)?
   - *Resolution:* **Desktop-first with tablet fallback; mobile card view below 768 px.** Minimum full-functionality viewport: 768 px. Below that, tables render as cards, filters collapse into a drawer, drag-to-reorder becomes an “Edit columns” sheet, touch targets ≥44×44 px.

7. **localStorage settings registry**
   - *Question:* Is there a localStorage settings registry and migration plan?
   - *Resolution:* **Yes.** Centralize under `ss_settings_v1` object. Add a migration helper on first load that reads old flat keys, copies values into the new object, then deletes the old keys. Group Admin toggles by concern.

### 12.4 Recommended additions to this wiki

The cross-review recommends the following living sections. Where possible they are already started above; the rest should be filled in as decisions are made:

1. **Glossary of terms** — unambiguous definitions of *active*, *flagged*, *active-only averages*, and each badge type.
2. **Filter semantics decision log** — what charts/stats include inactive or flagged listings; whether `use_active_avg` is split into `active_only` + `exclude_flagged`; default checkbox states per page.
3. **Flagging and admin authorization model** — who may flag/unflag/delete; how the backend validates it; canonical endpoints (`/api/flag` vs `/api/flag-listing`, `/api/unflag` vs `/api/unflag-listing/<id>`) and payload schemas.
4. **Detail modal architecture** — target pattern and migration plan for pages that deviate.
5. **localStorage settings registry** — single table of keys, default values, affected pages, and collision notes.
6. **Deal-badge / price-stats contract** — backend fields that feed badges and frontend helper usage rules.
7. **Responsive / accessibility baseline** — minimum viewport, touch targets, `prefers-reduced-motion` policy, ARIA checklist.
8. **Performance and data-loading patterns** — avoid N+1 history fetches, prefer dedicated stats endpoints, pagination plan if inventory grows.

### 12.5 Priority order for resolving contradictions

1. Agree on active/flagged semantics (unblocks filter UI and chart fixes).
2. Decide shared vs bespoke detail modal (prevents CSS work from landing on unused code).
3. Standardize flagging auth + payload + endpoints (security and consistency prerequisite).
4. Define a deal-badge / price-stats contract.
5. Create a localStorage registry + migration plan.
6. Refactor column customization into a shared component.
7. Mobile/responsive pass.

### 12.6 Known localStorage settings registry

The following keys are currently read or written across category pages. This table is a starting point for the formal registry recommended above.

| Legacy key | Used by | Default / purpose | Migration |
|------------|---------|-------------------|-----------|
| `showListingId` | GPU, Admin, Lenses | `true` (GPU/Admin), varies (Lenses) | Migrate to `ss_settings_v1.showListingId` and disambiguate Lenses usage under `ss_settings_v1.lenses.showAdminFields`. |
| `showGPUId` | GPU, Admin | `true` | Migrate to `ss_settings_v1.showGPUId`. |
| `showSourceDots` | GPU, CPU, Admin | `true` | Migrate to `ss_settings_v1.showSourceDots`. |
| `showSummaryFields` | GPU, CPU, SSD, Admin | `true` | Migrate to `ss_settings_v1.showSummaryFields`. |
| `showDeleteButtons` | GPU, Admin | `false` | Migrate to `ss_settings_v1.showDeleteButtons`. |
| `showGeForceInGPUName` | GPU, Admin | `true` | Migrate to `ss_settings_v1.showGeForceInGPUName`. |
| `cpuColumnOrder` / `cpuColumnVisibility` | CPU | page defaults | Migrate to `ss_settings_v1.columns.cpu`. |
| `ramColumnOrder` / `ramColumnVisibility` / `ramColumnCustomization` | RAM | page defaults | Migrate to `ss_settings_v1.columns.ram`. |
| `discovered_gpu_models` | GPU | `[]` JSON | **Delete** — FIRST badge is deprecated. |
| `discovered_cpu_models` | CPU | `[]` JSON | **Delete** — FIRST badge is deprecated. |
| `adminMode` / `adminPrebuiltToggle` | Computers | `false` | Migrate to `ss_settings_v1.adminMode` only; `adminPrebuiltToggle` is obsolete. |
| `showNotificationTips` | CPU | `true` | Migrate to `ss_settings_v1.showNotificationTips`. |

**Resolved 2026-07-24:** All settings live under a single versioned key **`ss_settings_v1`**. Add a migration helper in `base.html` that runs once, reads legacy keys, writes them into the new object, then removes the old keys. New code must never read the legacy keys directly.

### 12.7 Filter semantics decision log

| Decision | Current behavior | Proposed direction | Blocked by |
|----------|------------------|--------------------|------------|
| “Active only” listing filter | `is_active = true` on listing endpoints, default checked. | Keep as-is; persist per page under `ss_settings_v1.active.<page>`. | ✅ Resolved 2026-07-24. |
| “Active-only averages” / `use_active_avg` | GPU: excludes flagged, not active. RAM: active-only vs all-unflagged. CPU/SSD: no frontend toggle. | Split into `active_only` and `exclude_flagged` query params; default both **on**; remove/rename `use_active_avg`. | ✅ Resolved 2026-07-24. |
| Chart/stats flagged exclusion | GPU charts exclude flagged but include inactive; SSD/CPU charts include flagged; RAM stats include everything. | Make chart/stats endpoints mirror the default active+unflagged listing set unless “Show flagged” / “Include inactive” toggles are on. | ✅ Resolved 2026-07-24. |

---

## 13. Cross-Review: design × technical blind spots

This section is a cross-check between the design review (Section 10) and the technical review (Section 11). The latest resolved decisions live in **Section 12**. Section 13 is kept as a historical snapshot of the original 2026-07-23 cross-review; for current implementation direction, see Section 12 and the new dedicated Sections 14.1–14.5 below.

---

## 14. Resolved Implementation Contracts (2026-07-24)

After the 2026-07-23 design and technical reviews were merged into Sections 10–12, the maintainer asked separate designer and technical subagents for implementation recommendations and then made the following binding decisions. These contracts replace the open questions in Section 13.

### 14.1 Authentication and flagging authorization model

**Flagging, unflagging, and deleting listings are admin-only actions.** The dashboard currently exposes these controls on nearly every page, gated only by client-side `localStorage`. That is a security gap.

**Decision:**
- Add Flask-Login to `requirements.txt` if not already present.
- Store admin credentials via environment variables:
  - `SS_ADMIN_USER`
  - `SS_ADMIN_PASSWORD_HASH` (use `werkzeug.security.generate_password_hash`)
- Add decorators:
  - `@login_required`
  - `@admin_required` (custom decorator checking `current_user.is_admin`)
- Apply them to all destructive/admin endpoints:
  - `/api/flag`
  - `/api/flag-listing`
  - `/api/unflag`
  - `/api/unflag-listing/<id>`
  - Any delete-listing endpoint
- Add `/api/me` returning `{role: "admin" | "viewer"}`.
- Frontend renders flag/delete controls only after `/api/me` returns `role: admin`.
- Keep admin toggles in `localStorage` as UI preferences, but do not treat them as authorization.

**Endpoint canonicalization (still to be decided during implementation):**
- Pick one flag route and one unflag route; deprecate the other. Recommended: `/api/flag-listing` and `/api/unflag-listing/<id>` because they are already used by most category pages.
- Normalize payload: `{listing_id, reason}` (rename `comment` to `reason` everywhere).

### 14.2 Deal-badge contract

**Decision:** Keep only three badges everywhere: **NEW**, **STEAL**, **UNICORN**. Deprecate **FIRST** and **BUY**.

| Badge | Meaning | Backend source | Frontend rule | Color |
|-------|---------|----------------|---------------|-------|
| **NEW** | Listing first seen in the most recent import batch. | `first_seen_at::date == MAX(first_seen_at::date)` for the category. | Render if backend `is_new == true`. | Blue (`#3b82f6`) |
| **STEAL** | Price is ≥15% below the model average and the listing is not NEW. | `price_stats.below_avg == true` AND `price_stats.savings_pct >= 15`. | Render if both conditions true and not NEW. | Green (`#16a34a`) |
| **UNICORN** | Exceptional value percentile; exact threshold to be tuned after data pipeline is fixed. | Normalized `price_stats.unicorn_score` or percentile, computed from active+unflagged listings only. | Render if `price_stats.unicorn == true`. | Purple (`#9333ea`) |

**Important:** UNICORN computation must exclude flagged and inactive listings before the badge is enabled on any page. Until then, keep UNICORN hidden or mark it as beta.

**Dropped badges:**
- **FIRST** — client-only, device-specific, confusing. Remove `discovered_gpu_models` and `discovered_cpu_models` localStorage keys during migration.
- **BUY** — redundant with STEAL/UNICORN and depends on unstable all-time-min logic.

### 14.3 Detail-modal architecture

**Decision:** The target architecture is a **single shared modal** (`showSharedListingDetail` in `base.html`).

**Migration priority:**
1. Motherboards
2. Computers
3. Consoles
4. Lenses
5. Cameras / Cases

**Rules:**
- Category-specific content (monitor tier, GPU PassMark, lens mount) is injected as sections/tabs inside the shared shell, not as separate modal implementations.
- Modal becomes full-screen on viewports below ~640 px.
- Do not refactor modal CSS variables until the shared modal is the only (or dominant) modal; otherwise the work lands on unused bespoke code.

### 14.4 Active / flagged semantics

**Decision:** Two explicit toggles on every page that has listings:

| Toggle | Meaning | Default | Query param |
|--------|---------|---------|-------------|
| **Active listings only** | `listings.is_active = true` | On | `active_only=true` |
| **Exclude flagged listings** | No row in `flagged_listings` | On | `exclude_flagged=true` |

- Remove or rename `use_active_avg` everywhere.
- Listing endpoints, chart endpoints, and per-listing stats must respect both toggles by default.
- Persist each toggle per page under `ss_settings_v1.active.<page>` and `ss_settings_v1.flagged.<page>`.

### 14.5 Responsive and accessibility baseline

**Decision:**
- **Desktop-first** dashboard.
- **Minimum full-functionality viewport:** 768 px wide.
- **Below 768 px:** tables transform into cards, filters collapse into a drawer, drag-to-reorder becomes an “Edit columns” sheet, touch targets ≥44×44 px.
- Add `prefers-reduced-motion` guard in `base.html`:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
  ```
- Chart.js and drag-to-reorder must read `window.matchMedia('(prefers-reduced-motion: reduce)')` and disable animations when true.

---

## 16. Implementation Tasks

The actionable, copy-pasteable task prompts live in:
`SS-WEBSITE/docs/implementation_tasks.md`

(Companion file in the repo, not rendered inside the wiki to keep this page readable.)

### Format

Each task has: **Goal**, **File**, **Steps**, **Acceptance**. They are sized for a single coding session and do not create project-board tickets.

### Roadmap summary

| Phase | Progress | Theme | Key outcomes |
|-------|----------|-------|--------------|
| **P0** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Foundation | Flask-Login admin auth, `ss_settings_v1` registry, `price_stats` contract |
| **P1** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Active/flagged semantics | Two explicit toggles, correct stats/chart exclusion, per-page persistence |
| **P2** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Shared detail modal | `showSharedListingDetail` in `base.html`, `/api/detail/<category>/<id>`, page migration |
| **P3** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Badge & column unification | Shared NEW/STEAL/UNICORN component, gear icon in Actions header everywhere |
| **P4** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Responsive + a11y | `prefers-reduced-motion`, 768 px breakpoint, keyboard modal, table ARIA |
| **P5** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Performance + cleanup | Remove N+1 history fetches, canonicalize flag endpoints, delete dead code |
| **P6** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Self-hosting mirror | Linux server duplicate, nightly DB sync, local → remote code deploy |
| **P7** | `[░░░░░░░░░░░░░░░░░░░░] 0%` | Scale | Server-side filters for Computers, pagination for GPU/CPU, consistent API envelope |

### Execution order

P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7. P3 can overlap P2 once the shared modal contract is stable. P5 can start as soon as the first page is migrated to the shared modal.

---

## 17. Public Self-Hosting Mirror Plan (P6)

This section documents how to create a public duplicate of the dashboard + database on a local Linux server, keep it in sync with the local Windows development setup, and deploy website changes from the local machine.

### 17.1 Target architecture

| Role | Local (dev) | Remote (public) |
|------|-------------|-----------------|
| OS | Windows 10 | Linux (Ubuntu/Debian LTS on the LAN or VPS) |
| Web dashboard | `SS-WEBSITE/app.py` (Flask) | Same repo, `gunicorn` + `nginx` |
| Database | PostgreSQL `localhost:5433/ss_market` | PostgreSQL on Linux host |
| Images | `SS-CRAWLER/images/` | Synced subset or full mirror |
| Source control | Git repo on `G:\Github\SS-WEB-SCRAPPER` | `origin` on GitHub/GitLab/private Git server |

The remote server is not a separate codebase — it runs the same `SS-WEBSITE` and `SS-CRAWLER` checked out from Git. Only the database connection string and image path differ via environment variables.

### 17.2 Database sync strategy

Option A — **nightly dump/restore** (recommended for the mirror):

1. Local Windows creates a compressed PostgreSQL dump:
   ```powershell
   # run nightly or after scraping
   pg_dump -h localhost -p 5433 -U crawler -d ss_market -Fc > ss_market_$(Get-Date -Format yyyyMMdd_HHmmss).dump
   ```
2. Push the dump to the Linux server (`rsync` over SSH from WSL, or `scp`).
3. Remote server restores the dump into its PostgreSQL before replacing the live DB:
   ```bash
   # on Linux server
   pg_restore --clean --if-exists --create -d postgres /srv/ss-market/backups/ss_market_latest.dump
   ```

Option B — **incremental streaming replication**:
- Configure PostgreSQL logical replication from local → remote if both are reachable.
- More complex but near real-time; useful once the mirror becomes the primary public instance.

Option C — **one-command sync script**:
Add a PowerShell helper `sync_to_mirror.ps1` in the repo root:

```powershell
$RemoteHost = "ss-mirror.local"
$RemoteUser = "ssmarket"
$DumpFile = "ss_market_latest.dump"

Write-Host "Dumping local database..."
pg_dump -h localhost -p 5433 -U crawler -d ss_market -Fc -f $DumpFile

Write-Host "Uploading to mirror..."
scp $DumpFile "${RemoteUser}@${RemoteHost}:/srv/ss-market/backups/"

Write-Host "Restoring remote database..."
ssh "${RemoteUser}@${RemoteHost}" 'sudo /srv/ss-market/scripts/restore_db.sh /srv/ss-market/backups/ss_market_latest.dump'

Write-Host "Restarting remote web service..."
ssh "${RemoteUser}@${RemoteHost}" 'sudo systemctl restart ss-website'

Write-Host "Sync complete."
```

Then run:
```powershell
.\sync_to_mirror.ps1
```

### 17.3 Website deployment from local setup

Preferred method: **push-to-deploy via Git**.

1. Host the repo on a private Git remote (e.g., a `bare` repo on the Linux server or GitHub).
2. Add the remote:
   ```powershell
   git remote add mirror ssh://ssmarket@ss-mirror.local:2222/srv/git/SS-WEB-SCRAPPER.git
   ```
3. Push the local branch to the mirror:
   ```powershell
   git push mirror main
   ```
4. On the Linux server, a `post-receive` hook checks out the code, installs Python deps, runs migrations/static build if needed, and restarts the service:
   ```bash
   # /srv/git/SS-WEB-SCRAPPER.git/hooks/post-receive
   GIT_WORK_TREE=/srv/ss-market/app git checkout -f main
   cd /srv/ss-market/app/SS-WEBSITE
   source /srv/ss-market/venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart ss-website
   ```

Alternative method for quick fixes: **rsync over SSH** when Git access is not convenient:
```powershell
rsync -avz --delete /cygdrive/g/Github/SS-WEB-SCRAPPER/SS-WEBSITE/ ssmarket@ss-mirror.local:/srv/ss-market/app/SS-WEBSITE/
ssh ssmarket@ss-mirror.local 'sudo systemctl restart ss-website'
```

### 17.4 Linux server services (systemd)

`ss-website.service`:
```ini
[Unit]
Description=SS Website Flask app
After=network.target postgresql.service

[Service]
User=ssmarket
Group=ssmarket
WorkingDirectory=/srv/ss-market/app/SS-WEBSITE
Environment="DATABASE_HOST=localhost"
Environment="DATABASE_PORT=5432"
Environment="DATABASE_NAME=ss_market"
Environment="DATABASE_USER=ssmarket"
Environment="DATABASE_PASSWORD=<secret>"
Environment="IMAGES_ROOT=/srv/ss-market/images"
ExecStart=/srv/ss-market/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

`nginx` reverse proxy + static files:
```nginx
server {
    listen 80;
    server_name ss-mirror.local;

    location /static/ {
        alias /srv/ss-market/app/SS-WEBSITE/static/;
    }

    location /images/ {
        alias /srv/ss-market/images/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 17.5 Open decisions for P6

- Should the mirror also run the scraper (Linux can run Selenium/undetected-chromedriver), or should scraping stay on Windows and only data be synced?
- Should image sync be full (`rsync` of `SS-CRAWLER/images/`) or should remote download images independently?
- Should the public instance use HTTPS with a real domain, or stay LAN-only with a local certificate?
- Do we want a staging mirror in addition to production?

### 17.6 Acceptance criteria

- `sync_to_mirror.ps1` completes in one command and refreshes the public site.
- `git push mirror main` deploys the latest `SS-WEBSITE` code without manual SSH steps.
- Public URL shows the same listings, stats, and images as the local dashboard after sync.

---

## 18. Glossary

- **Reference table** – canonical product catalog (e.g., `gpu_reference`).
- **Listing** – one scraped marketplace row in `listings`.
- **Matched ID** – foreign key from a listing to a reference row.
- **Flag** – a user-marked bad listing excluded from stats.
- **STEAL badge** – price ≥15% below the active+unflagged model average; server-side.
- **UNICORN badge** – exceptional value percentile; server-side, currently beta until data pipeline excludes flagged/inactive listings.
- **NEW badge** – server-side, based on `first_seen_at`.
- **Deprecated:** **FIRST badge** (client-only `localStorage`, device-specific) and **BUY badge** (redundant).
