# SS-Crawler v2

GPU, CPU, and multi-category scraper for ss.com / Andele Mandele (Latvian marketplaces) with intelligent matching against a reference database.

**Andele Mandele? → Jump to [Andele at a glance](#andele-mandele--at-a-glance)** for the supported categories, every CLI flag, copy-paste examples, and the cleanup SQL.

## Features

- **Intelligent GPU Matching**: rapidfuzz-based matching against 627+ GPU models from cards.csv
- **Intelligent CPU Matching**: rapidfuzz-based matching against CPU models from cpus.csv
- **Andele Mandele Support**: scrape the Latvian marketplace with `--andele --gpu --cpu --ssd --ram --psu --motherboards --monitors --computers` (direct `/product-data/` API, no spotlight pollution)
- **Robust Error Handling**: Retry logic with error classification (retryable vs fatal)
- **Price Tracking**: Automatic price history, re-list detection
- **Stale Detection**: Auto-mark inactive listings after 7 days
- **Test Mode**: Scrape limited listings for debugging
- **HTML Snapshots**: Save failed parses for debugging

## Quick Start

### 1. Start Database
```bash
docker-compose up -d
```

Database will be initialized with:
- `gpu_reference` table (GPUs from cards.csv)
- `cpu_reference` table (CPUs from cpus.csv)
- All required tables and indexes
- Auto-backup enabled

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Scraper

The scraper supports every category on SS.com as well as the **Andele Mandele** marketplace. Use one or more `--<category>` flags with `python main.py scrape`.

> **If you only care about Andele Mandele:** jump straight to **[Andele at a glance](#andele-mandele--at-a-glance)** below. It has the supported categories, all run-control flags, and copy-paste examples.

#### Available categories

| Flag | SS.com source | Andele Mandele source |
|------|---------------|-----------------------|
| `--gpu` | Video cards / GPUs | ✅ |
| `--cpu` | Processors / CPUs | ✅ |
| `--ssd` | Solid-state drives | ✅ |
| `--ram` | Memory modules | ✅ |
| `--psu` | Power supplies | ✅ |
| `--cases` | PC cases | — |
| `--motherboards` | Motherboards | ✅ |
| `--monitors` | Monitors | ✅ |
| `--consoles` | Gaming consoles | — |
| `--lenses` | Camera lenses | — |
| `--cameras` | Camera bodies | — |
| `--computers` | Complete desktop computers | ✅ |
| `--laptops` | Laptops | — |
| `--andele` | Use the Andele Mandele source instead of SS.com | — |

#### Andele Mandele — supported categories

| Category | Flag | Andele attribute ID | Andele filter URL (under `https://www.andelemandele.lv/perles/tehnika/datori/`) |
|----------|------|---------------------|----------------------------------------------------------------------|
| GPU | `--andele --gpu` | `409` | `#order:actual/attributes:409` |
| CPU | `--andele --cpu` | `405` | `#order:actual/attributes:405` |
| SSD | `--andele --ssd` | `404` | `#order:actual/attributes:404` |
| RAM | `--andele --ram` | `406` | `#order:actual/attributes:406` |
| PSU | `--andele --psu` | `415` | `#order:actual/attributes:415` |
| Computer | `--andele --computers` | `413` | `#order:actual/attributes:413` |
| Monitor | `--andele --monitors` | `578` | `#order:actual/attributes:578` |
| Motherboard | `--andele --motherboards` | `403` | `#order:actual/attributes:403` |

Note: Andele Mandele has no first-class categories for "cases", "consoles", "lenses", "cameras", or "laptops" — only the eight component/PC categories above are exposed via the scraper. The `--andele` flag must be combined with a category flag.

#### Andele Mandele — at a glance

A single block of everything you need to scrape Andele. Details live in the sections below; this is the cheat sheet.

**Supported categories** (combine with `--andele`):

| Flag                       | What it scrapes              | Andele attribute |
|----------------------------|------------------------------|-----------------:|
| `--andele --gpu`           | Graphics cards               | `409`            |
| `--andele --cpu`           | Processors                   | `405`            |
| `--andele --ssd`           | Solid-state drives           | `404`            |
| `--andele --ram`           | Memory modules               | `406`            |
| `--andele --psu`           | Power supplies               | `415`            |
| `--andele --motherboards`  | Motherboards                 | `403`            |
| `--andele --monitors`      | Monitors                     | `578`            |
| `--andele --computers`     | Complete desktop computers   | `413`            |

**One-liner examples** (most common):

```bash
# Test mode — a small batch, no DB writes, no backup
python main.py scrape --andele --gpu --test --dry-run --no-backup

# All 8 Andele categories, unlimited pages
python main.py scrape --andele --gpu --cpu --ssd --ram --psu --motherboards --monitors --computers --max-pages 0

# Tight batch of motherboards with strict matching
python main.py scrape --andele --motherboards --limit 100 --confidence 0.85

# Dry-run RAM to preview what would be written
python main.py scrape --andele --ram --dry-run --max-pages 0

# Single Andele URL — parse + save rendered HTML for debugging
python main.py test-url "https://www.andelemandele.lv/v/dators/abc123" --andele --gpu --save-html
```

**All Andele-compatible CLI flags** (combine freely):

| Flag (short)          | Default           | Purpose                                                                |
|-----------------------|-------------------|------------------------------------------------------------------------|
| `--test` / `-t`       | off               | Fetch only the first page of listings (quick sanity check)            |
| `--limit` / `-l`      | `0` (unlimited)   | Stop after N listings                                                  |
| `--max-pages` / `-p`  | `5`               | Stop after N pages (`0` = unlimited)                                   |
| `--dry-run` / `-n`    | off               | Parse and print, **don't** write to the DB                            |
| `--no-backup`         | off               | Skip the pre-scrape `pg_dump` snapshot                                 |
| `--confidence`        | `0.70`            | Minimum matcher confidence (0.0–1.0)                                   |
| `--save-html`         | off (test-url)    | Save the rendered listing HTML to `logs/html_samples/`                 |

**Andele image handling** — the scraper always downloads the `.jpg` version (not `.webp`) from the Andele CDN so files are consistent across re-scrapes and re-listings. See [Image format](#image-format-always-jpg) below for the full writeup.

**Cleanup query** — if the old browser-only scraper wrote spotlight-polluted Andele listings to your DB, see [Cleaning up stale Andele listings](#cleaning-up-stale-andele-listings) for the SQL to find and remove them.

**How it works** — Andele's `/perles/tehnika/datori/` page is a Vue.js SPA; the category filter is applied client-side after JS runs, so a naive HTML scrape picks up the spotlight carousel instead of the real results. The scraper bypasses that by calling Andele's direct `/product-data/` API with a base64-encoded filter payload — see [How the Andele scraper works](#how-the-andele-scraper-works) below for the request shape and a worked example.

#### How the Andele scraper works

The Andele Mandele `/perles/tehnika/datori/` page is a Vue.js SPA. The category
filter (`#order:actual/attributes:<id>`) is applied **client-side** after
JavaScript runs, so a naive HTML scrape picks up the **spotlight ad carousel**
(random featured items at the top of the page) instead of the real
category-filtered results.

To work around this, the Andele scraper uses the **direct `/product-data/`
API endpoint** that powers the SPA's listing grid:

```
GET https://www.andelemandele.lv/product-data/?filter=<base64 json>
```

Where the decoded filter payload looks like:

```json
{"category":{"id":368},"order":"actual","attributes":["409"]}
```

This returns `{html: <article cards>, count: 21}` and is **truly filter-correct**
— no spotlight pollution, no JS race-conditions. Each listing is then
fetched individually for the full title/description and run through the
existing GPU/CPU/SSD/RAM/PSU/Monitor/Motherboard matchers.

A browser-based fallback is still available for cases where the API is
unreachable, but the API path is the default and recommended approach.

#### Image format (always `.jpg`)

Andele serves both `.webp` and `.jpg` from the same image CDN path
(`static*.andelemandele.lv`). The scraper always downloads the `.jpg`
version:

- `.webp` URLs from the API are transparently rewritten to `.jpg` before
  download (verified 2026-08-20: same path returns `image/webp` ≈80KB
  vs `image/jpeg` ≈230KB).
- Files are saved as `<base_listing_id>_<url_hash>.jpg` regardless of
  the original extension.
- Re-listed items (`<id>_v2`, `<id>_v3`) share the same image folder so
  duplicate downloads are avoided — the second scrape just reuses the
  cached file from disk.

This is implemented in `src/utils/image_downloader.py`
(`ImageDownloader._normalize_image_url()`). It is a no-op for non-Andele
sources (ss.com, displayspecifications.com, etc.) which already serve
`.jpg`/`.png`.

#### Cleaning up stale Andele listings

The spotlight-pollution bug in the old browser-only path may have written
some non-category-matching listings to the `listings` table. To clean them
up:

```sql
-- Preview: count of Andele listings whose category doesn't match the
-- expected reference (matched_gpu_id is set but category='gpu' missing, etc.)
SELECT id, listing_id, title, category, price_eur, source
FROM listings
WHERE source = 'andelemandele'
  AND (
    (category = 'gpu'        AND matched_gpu_id IS NULL) OR
    (category = 'cpu'        AND matched_cpu_id IS NULL) OR
    (category = 'ssd'        AND matched_ssd_id IS NULL) OR
    (category = 'ram'        AND matched_ram_id IS NULL) OR
    (category = 'psu'        AND matched_psu_id IS NULL) OR
    (category = 'monitor'    AND monitor_model_id IS NULL) OR
    (category = 'motherboard'AND motherboard_model_id IS NULL)
  );

-- Hard delete (use with care):
DELETE FROM listings
WHERE source = 'andelemandele'
  AND (
    (category = 'gpu'        AND matched_gpu_id IS NULL) OR
    (category = 'cpu'        AND matched_cpu_id IS NULL) OR
    (category = 'ssd'        AND matched_ssd_id IS NULL) OR
    (category = 'ram'        AND matched_ram_id IS NULL) OR
    (category = 'psu'        AND matched_psu_id IS NULL) OR
    (category = 'monitor'    AND monitor_model_id IS NULL) OR
    (category = 'motherboard'AND motherboard_model_id IS NULL)
  );
```

#### Examples

**Scrape GPUs on SS.com:**
```bash
python main.py scrape --gpu
```

**Scrape CPUs:**
```bash
python main.py scrape --cpu
```

**Scrape a few common categories:**
```bash
python main.py scrape --gpu --cpu --ssd --ram
```

**Scrape every SS.com category in one run:**
```bash
python main.py scrape --gpu --cpu --ssd --ram --cases --psu --motherboards --monitors --consoles --lenses --cameras --computers --laptops
```

Or use the PowerShell helper from the repo root:
```powershell
.\run_all_scrapers.ps1
```

**Andele Mandele examples**

Scrape one category:
```bash
python main.py scrape --andele --gpu
python main.py scrape --andele --cpu
python main.py scrape --andele --ssd
python main.py scrape --andele --ram
python main.py scrape --andele --psu
python main.py scrape --andele --motherboards
python main.py scrape --andele --monitors
python main.py scrape --andele --computers
```

Scrape multiple Andele categories in one run:
```bash
python main.py scrape --andele --gpu --cpu --ssd --ram
python main.py scrape --andele --gpu --cpu --ssd --ram --psu --motherboards --monitors --computers
```

Test a single Andele URL (parse without saving):
```bash
python main.py test-url "https://www.andelemandele.lv/v/dators/abc123" --andele --gpu --save-html
```

#### Andele Mandele — run-control flags

All of the run-control flags below work on both SS.com and Andele. They can be combined with any category flag (`--andele --gpu --test --limit 50 --max-pages 0 --dry-run` is a valid combination).

| Flag (short) | Default | Description |
|--------------|---------|-------------|
| `--test` / `-t` | off | Test mode — fetch only the first page of listings (faster, useful for debugging) |
| `--limit` / `-l` | `0` | Maximum listings to scrape per run. `0` = unlimited. Stops once the limit is hit |
| `--max-pages` / `-p` | `5` (laptops: `25`) | Maximum pages to walk through. `0` = unlimited |
| `--dry-run` / `-n` | off | Parse and print results but **don't** write to the database |
| `--no-backup` | off | Skip the automatic `pg_dump` snapshot that runs before each scrape |
| `--confidence` | `0.70` | Minimum matcher confidence to accept a match (0.0–1.0). Lower = more matches, more noise |
| `--save-html` | off | (test-url only) Save the rendered HTML of the listing to `logs/html_samples/` for debugging |

**Andele-specific example combinations**

```bash
# Pull a small batch of GPUs to verify the matcher is happy
python main.py scrape --andele --gpu --test --limit 20

# Walk every page of Andele motherboards (no page cap)
python main.py scrape --andele --motherboards --max-pages 0

# Dry-run a full Andele RAM scrape to see what would be written
python main.py scrape --andele --ram --dry-run --max-pages 0

# Skip the pre-scrape DB backup for a quick rescrape
python main.py scrape --andele --gpu --no-backup --limit 100

# Lower the match threshold to capture more ambiguous titles (more noise)
python main.py scrape --andele --cpu --confidence 0.55
```

**Test mode (limited listings):**
```bash
python main.py scrape --gpu --test --limit 1
python main.py scrape --cpu --test --limit 1
python main.py scrape --andele --gpu --test --limit 1
python main.py scrape --andele --motherboards --test --limit 1
```

**Scrape unlimited pages:**
```bash
python main.py scrape --cpu --max-pages 0
python main.py scrape --andele --gpu --max-pages 0
```

**Limit to a specific number of listings:**
```bash
python main.py scrape --gpu --limit 50
python main.py scrape --andele --motherboards --limit 100
```

**Test single SS.com URL (GPU):**
```bash
python main.py test-url "https://www.ss.com/.../123.html" --gpu --save-html
```

**Test single SS.com URL (CPU):**
```bash
python main.py test-url "https://www.ss.com/.../123.html" --cpu --save-html
```

**View stats:**
```bash
python main.py stats
```

**View last scrape report:**
```bash
python main.py report
```

## Configuration

Edit `config.yaml`:

```yaml
scraper:
  test_mode: false
  max_listings: 0          # 0 = unlimited
  min_confidence_threshold: 0.70  # Skip if match < 70%
  save_html_samples: true
  stale_after_days: 7
  category_path: "/lv/electronics/computers/completing-pc/video/"  # GPU
  cpu_category_path: "/lv/electronics/computers/completing-pc/cpu/"  # CPU

database:
  host: localhost
  port: 5432
  # ...
```

## Category URLs

### SS.com (ss.lv)

**GPU Category:** https://www.ss.lv/lv/electronics/computers/completing-pc/video/

**CPU Category:** https://www.ss.lv/lv/electronics/computers/completing-pc/cpu/

### Andele Mandele (andelemandele.lv)

Base path: `https://www.andelemandele.lv/perles/tehnika/datori/` (Computers → Components)

The Andele scraper uses the **direct `/product-data/` API** (not the hash-fragment
URL — that's client-side only and would pick up the spotlight ad carousel). See
the "How the Andele scraper works" section above for details.

| Category | Andele attribute ID | Andele URL (for reference) |
|----------|---------------------|----------------------------|
| GPU | `409` | `https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:409` |
| CPU | `405` | `…#order:actual/attributes:405` |
| SSD | `404` | `…#order:actual/attributes:404` |
| RAM | `406` | `…#order:actual/attributes:406` |
| PSU | `415` | `…#order:actual/attributes:415` |
| Computer | `413` | `…#order:actual/attributes:413` |
| Monitor | `578` | `…#order:actual/attributes:578` |
| Motherboard | `403` | `…#order:actual/attributes:403` |

## Architecture

```
┌──────────────────────────────────────────────┐
│              CLI (main)                      │
│  --gpu --cpu --ssd --ram                     │
│  --andele (switches source to Andele)        │
│  --test-url --stats --report                 │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────┴───────────────────────────┐
│           Scraper Engine                     │
│  ┌────────────────┐  ┌─────────────────────┐ │
│  │  SS.com        │  │  Andele Mandele     │ │
│  │  per-category  │  │  /product-data/     │ │
│  │  HTTP+selenium │  │  direct API         │ │
│  │  scrapers      │  │  + per-listing      │ │
│  │                │  │    browser fetch    │ │
│  └────────┬───────┘  └──────────┬──────────┘ │
│           └──────────┬─────────┘             │
│  ┌───────────────────┴──────────────┐         │
│  │  Matchers (rapidfuzz):          │         │
│  │  GPU, CPU, SSD, RAM, PSU,       │         │
│  │  Monitor, Motherboard, Computer │         │
│  └───────────────────┬──────────────┘         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────┴───────────────────────┐
│             Repository Layer                 │
│  - Listings (unified source='ss.com' or     │
│    source='andelemandele')                   │
│  - Price History                            │
│  - Scrape Runs                              │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────┴───────────────────────┐
│              PostgreSQL                      │
│   (host=localhost, port=5433, db=ss_market) │
└──────────────────────────────────────────────┘
```

## Testing

```bash
pytest tests/ -v
```

Test fixtures are in `tests/fixtures/`.

## Database Schema

**listings**: Core scraped data with lifecycle tracking (supports both GPU and CPU)
**price_history**: Append-only price changes
**gpu_reference**: GPU models from cards.csv
**cpu_reference**: CPU models from cpus.csv
**debug_snapshots**: Failed parse HTML samples
**scrape_runs**: Session tracking with category support

## DBeaver Connection

- Host: `localhost`
- Port: `5432`
- Database: `ss_market`
- User: `crawler`
- Password: `crawler_pass`

## License

MIT
