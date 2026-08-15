# SS-WEB-SCRAPPER Onboarding — Read This First

_Last updated: 2026-07-06 by main agent (lesson: task T190 came from the project board, not `ASSIGNMENT.md`)._

This file is a self-contained briefing for any future model/agent that picks up work on the SS-WEB-SCRAPPER suite. It fits in ~256k token budgets by being dense and skip-friendly. Read top-to-bottom once, then use it as a reference.

---

## 1. What This Project Is

A web-scraping + dashboard system for PC hardware listings and benchmarks. It collects listings from marketplace sites, matches them to canonical hardware models, and exposes pages/stats/charts.

Primary repo: `G:\Github\SS-WEB-SCRAPPER`
Main dashboard: `G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE` (Flask app)

### Sub-projects

| Sub-project | Path | Status | What it does |
|-------------|------|--------|--------------|
| SS-WEBSITE dashboard | `SS-WEBSITE\` | Working | Flask + Jinja2 + PostgreSQL dashboard |
| SS-Crawler V2 GPU scraper | `SS-WEB-SCRAPPER\` root / `SS-Crawler` legacy | Working | GPU listing scraper with matching algorithms |
| CPU-Benchmarks Java scraper | `cpu-spec-dataset\CPU-BENCHMARKS\` | Build OK, runtime 0 rows issue | Selenium Java scraper for cpubenchmark.net |
| CPU-PRICES scraper | `cpu-spec-dataset\CPU-PRICES\` | Working | PCPartPicker CPU price scraper |
| Cinebench R23 scraper | `cpu-spec-dataset\CPU-BENCHMARKS\cinebench_scraper_v3.py` | Ready | cpu-monkey.com div-based scraper |
| Cinebench R26 scraper | `cpu-spec-dataset\CPU-BENCHMARKS\cinebench_r26_scraper.py` | Ready | Cinebench 2026 scraper |
| Facebook scraper extension | `facebook-scraper-extension\` | Partial | Browser-extension + `extension_api.py` helper |

---

## 2. Dashboard Architecture

### Stack
- **Backend:** Flask (`app.py`)
- **Templates:** Jinja2 in `SS-WEBSITE\templates\`
- **DB:** PostgreSQL (port 5433 default, user `crawler`, DB `ss_market`)
- **Static assets:** `SS-WEBSITE\static\`
- **Image folders:** outside repo under `G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/...`

### Pages
- `/` — Dashboard stats
- `/gpu` — GPU listings
- `/cpu` — CPU listings + benchmark charts
- `/models` — Aggregated GPU/CPU model stats
- `/unmatched` — Manual review for unmatched listings
- `/admin` — Admin panel
- `/ssd`, `/motherboards`, `/monitors`, `/lenses`, `/computers` — Category pages
- `/project-board` — Kanban-style task board (see Section 7)

### Key API conventions
- Most listing endpoints return JSON arrays directly (e.g. `/api/gpus`, `/api/cpus`, `/api/motherboards`).
- Detail endpoints return `{"success": true, "listing": ..., "breakdown": ...}` (e.g. `/api/computers/<id>`).
- Stats endpoints return `{"success": true, "stats": ...}`.

### Database tables you will touch
- `listings` — scraped listings, all categories, has `matched_*_id` columns
- `gpu_reference`, `cpu_reference`, `ssd_reference`, `ram_reference`, `motherboard_models`, `monitor_models`, `lens_reference` — canonical models
- `price_history` — per-listing price changes
- `flagged_listings` — listings excluded from calculations
- `cpu_complete_data`, `cpu_benchmarks_r23`, `cpu_benchmarks_r26`, `cpu_benchmarks_passmark` — benchmark data

---

## 3. Running the Dashboard

```powershell
cd G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE
python app.py
# http://localhost:5000
```

Docker alternative:
```bash
docker-compose -f docker-compose-website.yml up
```

After any backend edit, restart the Flask process. The user runs it manually; there is no hot-reload in production.

---

## 4. Matching System

Listings have a `category` and `matched_*_id` referencing a canonical reference table. Confidence scores (`confidence_score`, `cpu_confidence_score`, `ssd_confidence_score`, etc.) are stored per category.

### GPU matching
- Located historically in `SS-Crawler` / GPU scraper code.
- Known pitfalls already fixed:
  - Intel Arc A380 matching to AMD Radeon R9 380
  - GeForce 9800 GT older Nvidia detection
  - RX Vega 56 / RX 570 confusion via stricter VRAM and vendor detection
  - ASUS/Gigabyte/MSI make both Nvidia and AMD cards, so brand-only vendor detection is unsafe.

### CPU matching
- Java scraper currently extracts 0 rows from cpubenchmark.net (debug logging added, issue open).
- R23/R26 data comes from `cpu-monkey.com`, scraped with undetected-chromedriver because of Cloudflare.

### Motherboard matching
- Uses `motherboard_models` table, `motherboard_model_id` on listings.

---

## 5. Known Bugs & Recently Fixed

### Fixed recently (check git/MEMORY.md for full list)
1. **T140 not visible in Assignment column** — frontend filter `taskMatchesFilters()` was hiding any task with `folder_id`/`future_folder_id` from regular columns. Now it only hides tasks whose `column` is literally `'future'`.
2. **Computers popup: `local variable 're' referenced before assignment`** — `app.py` used `re.search()` in `/api/computers/<id>` but never imported `re`. Added top-level `import re` and removed inline `import re` blocks.
3. **Motherboards CPU filter: `invalid input syntax for type integer`** — `/api/motherboards` passed `processor_number` string to `cpu_reference.id`. Now only uses `id` match if numeric, otherwise LIKE on `cpu_name`/`processor_number`.
4. **Motherboards CPU filter search box** — added a text search input to quickly find CPU models in the long dropdown.
5. **Project board: edit last reopen reason** — added inline Edit button on the most recent `reopen_history` entry with new `PUT /api/project-board/task/<id>/reopen-history/<idx>` endpoint.

### Critical: PostgreSQL port mismatch (listings didn't load)

There are **two PostgreSQL instances** running on this machine — one on port **5432** (empty DB) and one on port **5433** (real data with 1497 listings, 20272 monitor_models). The default port in `app.py` was hardcoded as `5432`. Changing it to `5433` (the correct one) fixed ALL pages that were returning empty/failing. **Always verify which port the actual database lives on before changing DB config**, and be aware that the standard PostgreSQL port (5432) may not be the one with data.

### Still open / watch out for
- CPU-Benchmarks Java scraper extracts 0 rows (T136-ish area).
- Some pages call functions that no longer exist (`showListingDetail` in motherboards page, reported in T016 reopen history).
- CPU page date_posted missing for some listings (T005 reopened).
- SSD badge not showing in listings list (T072).

---

## 6. Code Patterns to Follow

### When adding a new listing filter
1. Read the current `get_*()` route in `app.py`.
2. Add a `request.args.get('param')`.
3. Append to `where_clauses` and `params`, then execute with `cursor.execute(query, params)`.
4. Watch type safety (int ids vs string names).

### When editing project board
- Board data: `SS-WEBSITE\data\project_board.json`
- Template/frontend: `SS-WEBSITE\templates\project_board.html`
- Backend APIs: in `app.py`, search for `@app.route('/api/project-board/...`
- Logging: `board_logger.py` writes to `SS-WEBSITE\data\project_board.log`

### Moving a task between columns (CRITICAL)
Moving a task from one column to another requires **two** changes in `project_board.json`:
1. **Update `column` field** on the task object to the destination column ID.
2. **Move the task object** from the source column's `tasks` array to the destination column's `tasks` array. The frontend renders tasks based on which column's array they live in, not just the `column` field.

### Editing project_board.json safely (CRITICAL)
- **NEVER use PowerShell `ConvertTo-Json` + `Set-Content`** to modify `project_board.json`. `Set-Content` adds a UTF-8 BOM (byte order mark) which breaks Python's `json.load()`, causing the Flask app to return an empty board.
- **Instead, use Python** to read, modify, and write the JSON:
  ```python
  with open(path, 'r', encoding='utf-8') as f:
      data = json.load(f)
  # ... modify data ...
  with open(path, 'w', encoding='utf-8') as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
  ```
- When using the `edit` tool on the raw JSON text, make sure to match the exact indentation. The file uses 2-space indent.

### When adding an API endpoint
- Keep route definitions in `app.py`.
- Use `RealDictCursor` for dict-style rows.
- Convert `Decimal` to `float` via `convert_decimal_to_float()` before `jsonify()`.
- Close cursor + conn in `finally` or on every exit path.

---

## 7. Project Board — Special Rules

The project board is the user's primary task tracker. Treat it as the source of truth.

### Columns
`problems` → `assignment` → `progress` → `talking` (review) → `solved` → `future` (folders)

### Where tasks actually live (important)

`ASSIGNMENT.md` in the workspace root is **not** the source of truth for the project board. It is a convenience scratchpad that the agent writes to. The real board data is in:

```
G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_board.json
```

When a user says "take task T190 from assignment" but T190 is **not** listed in `ASSIGNMENT.md`, the agent must:

1. Read `SS-WEBSITE\data\project_board.json` directly.
2. Search all columns for the task ID (tasks can be in `problems`, `assignment`, `progress`, `talking`, `solved`, or `future`).
3. Note the task's `column`, `title`, `page`, `category`, `fix`, and `code_snippet` fields.
4. Update `ASSIGNMENT.md` to track the task as in-progress.

#### T190 example (real case, 2026-07-06)
- User: "Take task T190 from assignment and try to solve it."
- `ASSIGNMENT.md` only had T180–T187; T190 was not there.
- T190 was found in `project_board.json` under the `assignment` column with this stored snippet:
  ```html
  <select id="cpu-select" class="component-select" onchange="selectComponent('cpu', this.value)">
    <option value="">Select CPU...</option>
    <option value="214" data-name="Intel Core i7-6700K">Intel Core i7-6700K - €72.50</option>
  </select>
  ```
- The snippet revealed that "CPU box" meant the **PC Builder CPU dropdown**, not the CPU listings page. Reading the snippet prevented solving the wrong problem.

### How to move a task between columns

The board JSON has a top-level `columns` array. Each column has:
- `id` — machine name used in task objects (`assignment`, `progress`, `talking`, `solved`, `future`, `problems`).
- `title` — display label (`Assignment`, `In Progress`, `Review`, `Solved`, `Future`, `Problems`).
- `tasks` — array of task objects that currently render in that column.

To move a task, you must update **both** the task's `column` field and the physical array it lives in:

1. Find the task in the source column's `tasks` array.
2. Remove it from that array.
3. Append it to the destination column's `tasks` array.
4. Set `task.column = destination_column_id`.
5. Update `task.updated` and `task.updated_at` to the current ISO timestamp.

**Always use Python to edit the file**, not PowerShell `Set-Content`, because PowerShell adds a UTF-8 BOM that breaks `json.load()`:

```python
import json
from datetime import datetime, timezone

path = r'G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\data\project_board.json'
with open(path, 'r', encoding='utf-8') as f:
    board = json.load(f)

# Move T190 from assignment to talking
for col in board['columns']:
    if col['id'] == 'assignment':
        task = next(t for t in col['tasks'] if t['id'] == 'T190')
        col['tasks'].remove(task)
        now = datetime.now(timezone.utc).isoformat()
        task['column'] = 'talking'
        task['updated'] = now
        task['updated_at'] = now
        for dest in board['columns']:
            if dest['id'] == 'talking':
                dest['tasks'].append(task)
                break
        break

with open(path, 'w', encoding='utf-8') as f:
    json.dump(board, f, indent=2, ensure_ascii=False)
```

The frontend renders the board from the column arrays, so missing either step (field update or array move) causes the task to appear in the wrong column or disappear.

### Future folders
- A task with `future_folder_id` or `folder_id` assigned but `column != 'future'` stays visible in its working column.
- Only when `column == 'future'` is it physically stored in the Future column.
- The `includeFuture` filter controls whether future-column tasks are shown when browsing; working-column tasks remain visible.

### Reopening
- Tasks in `talking`/`solved` dragged to `assignment`/`problems` trigger a reopen modal.
- `reopen_history` stores `{reopened_at, update, previous_completed_at}`.
- Only the **last** reopen reason is editable inline in the task detail popup.

### Task fields
Common fields: `id`, `title`, `page`, `category`, `priority`, `fix`, `column`, `created`, `updated`, `linked_tasks`, `linked_task_id`, `relationship_type`, `future_folder_id`, `folder_id`, `reopen_history`, `completed_at`, `code_snippet`, `language`, `special`.

---

## 8. Agent Workflow / Cron

### Deferred discovery queue (new)
Mid-work discoveries can be queued without creating tickets immediately.
- Queue script: `C:\Users\goldm\.openclaw\workspace\create_discovery.py`
- Processor: `C:\Users\goldm\.openclaw\workspace\cron_process_discoveries.py`
- Cron job `check-assignments` (id `7f0c11ae-4035-459e-999b-02b77bb97b96`) currently **disabled**. When enabled it runs every 10 minutes:
  1. `cron_process_discoveries.py` — create queued discovery tickets in Problems
  2. `cron_dispatch.py check` — decide whether to process (rules in the file)
  3. If CHECK, scan board and work on Assignment/Progress tasks.

### Assignment rules (from MEMORY.md / user preference)
Process tasks in this order:
1. Re-opened tasks first (highest priority)
2. New tasks in Assignment by task ID ascending
3. Tasks already In Progress continue until completion

Always complete tasks in Assignment/Progress before stopping. Workflow: Assignment → In Progress → Review → Solved.

---

## 9. Environment & Credentials

- Python: CPython 3.10
- Node: v24.13.1
- OS: Windows 10
- PostgreSQL: localhost:5433, user `crawler`, db `ss_market`
- Maven for Java scraper: `C:\ProgramData\chocolatey\lib\maven\apache-maven-3.9.14\bin\mvn.cmd`
- JDK: `C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot\bin\java.exe`

No secrets are stored in this file. DB password is in env or config; don't hardcode it.

---

## 10. How to Update This File

When you make a significant architecture change, fix a recurring bug, or the user changes workflow rules:
1. Edit `C:\Users\goldm\.openclaw\workspace\ONBOARDING.md`.
2. Keep it dense.
3. Update the `Last updated` line.
4. Commit with a message like `docs: update ONBOARDING.md`.

If something is missing or ambiguous, ask the user before guessing — especially around task priorities and which page/category a fix belongs to.
