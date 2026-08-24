# displayspec_scraper.py

Scraper for [displayspecifications.com](https://www.displayspecifications.com) — a community-maintained
monitor specification database. Outputs to the `monitors_additional` table in `ss_market`.

## Why

- `monitor_models` (the project's reference table) stores brand, model, size, resolution, refresh
  rate, panel type and a heuristic `nits` value (250–1000). About 20,272 rows.
- `monitors_additional` stores the FULL spec sheet from displayspecifications.com:
  size, resolution, panel manufacturer + model, bit depth, FRC, brightness (cd/m²),
  color gamut (sRGB / Adobe RGB / DCI P3), static contrast, viewing angles, response time,
  VESA mount, tilt/swivel/pivot, weight (with/without stand), power consumption, full
  connectivity list, features list, etc.
- Together they let us:
  1. **Augment the reference** with the ~35+ fields the reference is missing (e.g. panel mfr,
     color gamut, weight, VESA, tilt range).
  2. **Calibrate the nits heuristic** with real manufacturer numbers (see comparison below).
  3. **Discover missing models** that exist on the site but not in the project's reference
     (e.g. 12 of 34 Cooler Master models on the site are NOT in `monitor_models`).

## Anti-bot

displayspecifications.com uses a custom JS click-challenge ("Verify you are human") on every
new browser session. The scraper bypasses it with Playwright by:
- Overriding `navigator.webdriver = false` before the page loads.
- Clicking the `.checkbox > div` once.
- Saving the resulting `_hv` cookie to `ds_cookies.json` for reuse.

Cookies are valid for the session (about 7 days per the `Max-Age=604800` set in the script).

## Usage

```bash
# Single brand
python displayspec_scraper.py --brand-url "https://www.displayspecifications.com/en/brand/505a43"

# Single model (for testing)
python displayspec_scraper.py --model-url "https://www.displayspecifications.com/en/model/1cba4662"

# Multiple brands from a file (one URL per line, # comments OK)
python displayspec_scraper.py --brand-list brands.txt

# Just 3 models, dry-run (no DB writes)
python displayspec_scraper.py --brand-url "https://..." --max 3 --dry-run

# Custom DB
python displayspec_scraper.py --brand-url "..." --db-url "postgresql://user:pass@host:port/db"
```

## Current state (after first run)

| brand          | in scraper | in ref | matched | new discoveries |
|----------------|-----------:|-------:|--------:|----------------:|
| Cooler Master  |         34 |     27 |      22 |              12 |

### Field coverage (after parser fixes, Cooler Master, 34 rows)

| field                          | filled | pct  |
|--------------------------------|-------:|-----:|
| `colors` / `colors_bits`       |   34/34 | 100% |
| `colors_offered`               |   34/34 | 100% |
| `weight_with_stand_kg`         |   30/34 |  88% |
| `weight_no_stand_kg`           |   26/34 |  76% |
| `port_hdmi_count`              |   34/34 | 100% |
| `port_dp_count`                |   25/34 |  74% |
| `port_vga_count`               |    9/34 |  26% |
| `port_audio_out_count`         |   31/34 |  91% |
| `feature_hdr_ready`            |    7/34 |  21% |
| `feature_freesync`             |    3/34 |   9% |
| `feature_flicker_free`         |   31/34 |  91% |
| `feature_adaptive_sync`        |   23/34 |  68% |
| `feature_low_blue_light`       |   34/34 | 100% |

The remaining gaps are models whose displayspecifications.com page genuinely does not
list that field (not parser bugs).

### Parser gotchas (now fixed)

- **Label collisions on `<td>Colors</td>`.** The page has TWO rows with the same label:
  one for the panel color count (e.g. "16777216 colors\n24 bits") and one for the
  offered chassis color (e.g. "Black"). They differ only in the `<p>` description.
  The parser now passes the description text and uses it to dispatch. Coverage went
  from 0% to 100% on both fields.
- **Label "Weight" vs "Weight with stand".** The "Weight without stand" row on this
  site is labelled just `Weight` (with `<p>Weight without stand in different
  measurement units.</p>`), and the "Weight with stand" row is labelled
  `Weight with stand`. The parser reads the `<p>` to disambiguate. Coverage went from
  0% to 76% on `weight_no_stand_kg`.
- **Connectivity and Features splitting.** The raw `connectivity` and `features` columns
  hold newline-separated lists. The parser now also writes structured per-port counts
  (`port_hdmi_count`, `port_dp_count`, `port_vga_count`, `port_usb_c_count`,
  `port_audio_out_count`, ...) and version columns (`port_hdmi_max_version`, etc.), and
  per-feature boolean flags (`feature_hdr_ready`, `feature_freesync`, `feature_kvm`,
  `feature_crosshair`, `feature_low_blue_light`, ...).

### Nits calibration (Cooler Master, scraper vs heuristic)

| model           | ref (heuristic) | scraper (mfr spec) | Δ       | notes                          |
|-----------------|----------------:|-------------------:|--------:|--------------------------------|
| GZ2711 (OLED)   |             400 |                150 |   -250  | OLED sustained ≠ peak          |
| GM27-FQ         |             400 |                400 |      0  | matches                        |
| GM27-CFX        |             475 |                300 |   -175  | 240Hz VA but no HDR bump       |
| GP2711 (HDR)    |             425 |                600 |   +175  | HDR600 panel, heuristic missed |
| GM34-CWQ2       |             425 |                320 |   -105  | 180Hz but lower brightness     |
| GM27-FFS        |             400 |                250 |   -150  | 165Hz IPS, not 400             |

The heuristic is generally 50–250 nits too high. A future improvement: use the scraper's
real `nits` for known models and fall back to the heuristic only for models the scraper
hasn't seen.

## Backfill existing rows

If you change the parser, re-parse the existing rows without re-fetching the site:

```python
# backfill_monitors_additional.py (one-shot script)
# Reads source_url from monitors_additional, refetches the page (or uses a local
# HTML cache in %TEMP%\ds_html_cache), re-parses with the current parser,
# and UPSERTs the result.
```

Or just re-run the brand scraper — it UPSERTs on `source_id`, so existing rows are
overwritten in place.

## Next steps

1. Add more brand URLs (the user said they'd provide a full list after Cooler Master).
2. Consider a periodic re-scrape to pick up new models as they're added to the site.
3. Add a `monitor_models.nits_source` column to track which rows have scraper-confirmed nits.
4. Add a "backfill" job: for each reference row, if there's a matching scraper row with a
   different nits, update the reference (or flag for manual review).
5. Expose `port_hdmi_count`, `feature_hdr_ready`, etc. as filters in the SS-WEBSITE monitor UI.
