# SS-Crawler v2

GPU, CPU, and multi-category scraper for ss.com / Andele Mandele (Latvian marketplaces) with intelligent matching against a reference database.

## Features

- **Intelligent GPU Matching**: rapidfuzz-based matching against 627+ GPU models from cards.csv
- **Intelligent CPU Matching**: rapidfuzz-based matching against CPU models from cpus.csv
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

#### Available categories

| Flag | What it scrapes |
|------|-----------------|
| `--gpu` | Video cards / GPUs |
| `--cpu` | Processors / CPUs |
| `--ssd` | Solid-state drives |
| `--ram` | Memory modules |
| `--cases` | PC cases |
| `--psu` | Power supplies |
| `--motherboards` | Motherboards |
| `--monitors` | Monitors |
| `--consoles` | Gaming consoles |
| `--lenses` | Camera lenses |
| `--cameras` | Camera bodies |
| `--computers` | Complete desktop computers |
| `--laptops` | Laptops |
| `--andele` | Use the Andele Mandele source instead of SS.com |

#### Examples

**Scrape GPUs on SS.com:**
```bash
python main.py scrape --gpu
```

**Scrape CPUs:**
```bash
python main.py scrape --cpu
```

**Scrape GPUs on Andele Mandele:**
```bash
python main.py scrape --andele --gpu
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

**Test mode (limited listings):**
```bash
python main.py scrape --gpu --test --limit 1
python main.py scrape --cpu --test --limit 1
```

**Scrape unlimited pages:**
```bash
python main.py scrape --cpu --max-pages 0
```

**Limit to a specific number of listings:**
```bash
python main.py scrape --gpu --limit 50
```

**Test single URL (GPU):**
```bash
python main.py test-url "https://www.ss.com/.../123.html" --gpu --save-html
```

**Test single URL (CPU):**
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

**GPU Category:** https://www.ss.lv/lv/electronics/computers/completing-pc/video/

**CPU Category:** https://www.ss.lv/lv/electronics/computers/completing-pc/cpu/

## Architecture

```
┌─────────────────┐
│   CLI (main)    │
│   --gpu --cpu   │
│   --test-url    │
│   --stats       │
└────────┬────────┘
         │
┌────────┴────────┐
│ Scraper Engine  │
│ - GPU Scraper   │
│ - CPU Scraper   │
│ - Crawler       │
│ - Parser        │
│ - Matcher       │
└────────┬────────┘
         │
┌────────┴────────┐
│  Repository     │
│ - Listings      │
│ - Price History │
│ - Scrape Runs   │
└────────┬────────┘
         │
┌────────┴────────┐
│   PostgreSQL    │
│ (Docker)        │
└─────────────────┘
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
