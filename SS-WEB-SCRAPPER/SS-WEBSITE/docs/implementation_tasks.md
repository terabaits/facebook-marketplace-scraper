# SS-WEB-SCRAPPER — Actionable Implementation Task Prompts

Each block below is a self-contained task prompt. Hand it to a coding subagent or run it directly.
Format: `T### — Title | Estimated time | Dependencies`.

---

## T000 — Ground rules for every task

Before starting any task below:
1. Read `G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\docs\project_wiki.md` Sections 12, 14, 16.
2. Do not create project-board tickets.
3. After code changes, run `python -m py_compile G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\app.py`.
4. Open the affected page in a browser. Test light and dark mode.
5. Update `docs/project_wiki.md` changelog (Section 6) with what changed.
6. Do not commit unless asked.

---

# Phase P0 — Foundation

## T001 — Add Flask-Login to requirements
**Goal:** Declare Flask-Login as a dependency.
**File:** `SS-WEBSITE/requirements.txt`
**Steps:**
1. Open `requirements.txt`.
2. If `Flask-Login` is not present, add `Flask-Login>=0.6.3` on its own line.
3. If `werkzeug` is not pinned, ensure it is present (Flask pulls it anyway).
**Acceptance:** `requirements.txt` contains `Flask-Login`.

---

## T002 — Configure Flask-Login in app.py
**Goal:** Initialize Flask-Login and load the admin user from env vars.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Add imports at the top:
   ```python
   from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
   from werkzeug.security import check_password_hash
   import os
   ```
2. After `app = Flask(__name__)`, add:
   ```python
   app.secret_key = os.environ.get('SS_SECRET_KEY', 'dev-secret-change-me')
   login_manager = LoginManager()
   login_manager.init_app(app)
   ```
3. Add a `User` class:
   ```python
   class User(UserMixin):
       def __init__(self, id, is_admin=False):
           self.id = id
           self.is_admin = is_admin
       def get_id(self):
           return self.id
   ```
4. Add `@login_manager.user_loader`:
   ```python
   @login_manager.user_loader
   def load_user(user_id):
       admin_user = os.environ.get('SS_ADMIN_USER')
       if user_id == admin_user:
           return User(user_id, is_admin=True)
       return None
   ```
5. Add `/api/me`:
   ```python
   @app.route('/api/me', methods=['GET'])
   def api_me():
       if current_user.is_authenticated and current_user.is_admin:
           return jsonify({'role': 'admin'})
       return jsonify({'role': 'viewer'})
   ```
6. Add login/logout routes (for session cookies):
   ```python
   @app.route('/login', methods=['POST'])
   def login():
       data = request.get_json() or request.form
       username = data.get('username', '')
       password = data.get('password', '')
       admin_user = os.environ.get('SS_ADMIN_USER')
       admin_hash = os.environ.get('SS_ADMIN_PASSWORD_HASH')
       if username == admin_user and admin_hash and check_password_hash(admin_hash, password):
           login_user(User(username, is_admin=True))
           return jsonify({'role': 'admin'})
       return jsonify({'error': 'Invalid credentials'}), 401

   @app.route('/logout', methods=['POST'])
   @login_required
   def logout():
       logout_user()
       return jsonify({'role': 'viewer'})
   ```
**Acceptance:**
- `python -m py_compile app.py` passes.
- `curl http://localhost:5000/api/me` returns `{"role":"viewer"}`.
- POST to `/login` with correct env credentials returns `{"role":"admin"}`.
- `/api/me` then returns `{"role":"admin"}`.

---

## T003 — Create admin_required decorator
**Goal:** Reusable decorator for admin-only endpoints.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Add:
   ```python
   from functools import wraps

   def admin_required(f):
       @wraps(f)
       @login_required
       def decorated_function(*args, **kwargs):
           if not current_user.is_admin:
               return jsonify({'error': 'Admin required'}), 403
           return f(*args, **kwargs)
       return decorated_function
   ```
2. Replace any existing manual admin checks with `@admin_required` on the following routes (search for `flag`, `unflag`, `delete` route definitions):
   - `/api/flag`
   - `/api/flag-listing`
   - `/api/unflag`
   - `/api/unflag-listing/<id>`
   - any delete-listing route
**Acceptance:**
- POST to each protected route without session returns 401.
- POST with a logged-in admin returns the original success response.
- `python -m py_compile app.py` passes.

---

## T004 — Add settings registry in base.html
**Goal:** Centralize all localStorage reads/writes under `ss_settings_v1`.
**File:** `SS-WEBSITE/templates/base.html`
**Steps:**
1. In a shared `<script>` block at the bottom of `base.html`, add:
   ```javascript
   const SETTINGS_KEY = 'ss_settings_v1';
   const DEFAULT_SETTINGS = {
     version: 1,
     theme: 'light',
     showListingId: true,
     showGPUId: true,
     showSourceDots: true,
     showSummaryFields: true,
     showDeleteButtons: false,
     showGeForceInGPUName: true,
     showNotificationTips: true,
     adminMode: false,
     active: {},
     flagged: {},
     columns: {},
   };

   function migrateSettings() {
     const raw = localStorage.getItem(SETTINGS_KEY);
     if (raw) return JSON.parse(raw);
     const legacyMap = {
       showListingId: 'showListingId',
       showGPUId: 'showGPUId',
       showSourceDots: 'showSourceDots',
       showSummaryFields: 'showSummaryFields',
       showDeleteButtons: 'showDeleteButtons',
       showGeForceInGPUName: 'showGeForceInGPUName',
       showNotificationTips: 'showNotificationTips',
       adminMode: 'adminMode'
     };
     const settings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
     for (const [oldKey, newKey] of Object.entries(legacyMap)) {
       const val = localStorage.getItem(oldKey);
       if (val !== null) {
         try { settings[newKey] = JSON.parse(val); } catch { settings[newKey] = val; }
       }
     }
     // column migration
     const cpuOrder = localStorage.getItem('cpuColumnOrder');
     const cpuVis = localStorage.getItem('cpuColumnVisibility');
     if (cpuOrder || cpuVis) {
       settings.columns.cpu = {};
       if (cpuOrder) settings.columns.cpu.order = JSON.parse(cpuOrder);
       if (cpuVis) settings.columns.cpu.visible = JSON.parse(cpuVis);
     }
     const ramOrder = localStorage.getItem('ramColumnOrder');
     const ramVis = localStorage.getItem('ramColumnVisibility');
     if (ramOrder || ramVis) {
       settings.columns.ram = {};
       if (ramOrder) settings.columns.ram.order = JSON.parse(ramOrder);
       if (ramVis) settings.columns.ram.visible = JSON.parse(ramVis);
     }
     // delete deprecated keys
     Object.keys(legacyMap).forEach(k => localStorage.removeItem(k));
     ['cpuColumnOrder', 'cpuColumnVisibility', 'ramColumnOrder', 'ramColumnVisibility',
      'ramColumnCustomization', 'adminPrebuiltToggle',
      'discovered_gpu_models', 'discovered_cpu_models'].forEach(k => localStorage.removeItem(k));
     localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
     return settings;
   }

   function getSettings() {
     const raw = localStorage.getItem(SETTINGS_KEY);
     if (!raw) return migrateSettings();
     return JSON.parse(raw);
   }

   function setSettings(settings) {
     localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
   }

   function getSetting(path, defaultValue) {
     const parts = path.split('.');
     let obj = getSettings();
     for (const p of parts) {
       if (obj == null || !(p in obj)) return defaultValue;
       obj = obj[p];
     }
     return obj;
   }

   function setSetting(path, value) {
     const parts = path.split('.');
     const settings = getSettings();
     let obj = settings;
     for (let i = 0; i < parts.length - 1; i++) {
       if (!obj[parts[i]]) obj[parts[i]] = {};
       obj = obj[parts[i]];
     }
     obj[parts[parts.length - 1]] = value;
     setSettings(settings);
   }

   (function initSettings() {
     if (!localStorage.getItem(SETTINGS_KEY)) migrateSettings();
   })();
   ```
2. Ensure the existing dark-mode script reads `getSetting('theme', 'light')` instead of `localStorage.getItem('theme')`, and `setSetting('theme', ...)` instead of `localStorage.setItem('theme', ...)`.
**Acceptance:**
- `console.log(getSettings())` returns an object with `version: 1`.
- If old `showListingId` exists, it is migrated and removed.
- Theme toggle still works after migration.

---

## T005 — Define the price_stats contract
**Goal:** Every listing endpoint returns a normalized `price_stats` object.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Add helper:
   ```python
   def price_stats_for_listing(listing, category):
       # listing is a dict/row with price and matched model info
       # category is one of the category strings used by the dashboard
       # Use existing aggregate helpers; this is a thin wrapper.
       # Return exactly this shape:
       return {
           'is_new': listing.get('is_new', False),
           'below_avg': listing.get('below_avg', False),
           'savings_pct': listing.get('savings_pct') or 0,
           'unicorn': listing.get('unicorn', False),
           'unicorn_score': listing.get('unicorn_score'),
           'avg': listing.get('model_avg_price'),
           'min': listing.get('model_min_price'),
           'max': listing.get('model_max_price'),
           'sample_size': listing.get('model_sample_size', 0)
       }
   ```
2. For each listing endpoint (`/api/gpus`, `/api/cpus`, `/api/rams`, `/api/ssds`, etc.), after fetching rows, add:
   ```python
   for row in listings:
       row['price_stats'] = price_stats_for_listing(row, 'gpu')  # adjust category
   ```
3. Update the SQL selects to include whatever fields `price_stats_for_listing` needs.
**Acceptance:**
- `curl http://localhost:5000/api/gpus` returns rows with `price_stats`.
- `curl http://localhost:5000/api/cpus` returns rows with `price_stats`.
- All fields in the contract are present, even if `None`/`0`.

---

# Phase P1 — Active / Flagged Semantics

## T006 — Split use_active_avg into active_only and exclude_flagged
**Goal:** Replace the misleading parameter.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Search for `use_active_avg` in `app.py`.
2. In each function, replace:
   ```python
   use_active_avg = request.args.get('use_active_avg', 'true').lower() == 'true'
   ```
   with:
   ```python
   active_only = request.args.get('active_only', 'true').lower() == 'true'
   exclude_flagged = request.args.get('exclude_flagged', 'true').lower() == 'true'
   ```
3. Replace `get_active_avg_clauses()` logic with two clauses:
   ```python
   active_clause = "l.is_active = true" if active_only else "1=1"
   flagged_clause = "NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)" if exclude_flagged else "1=1"
   ```
4. Apply both to listing queries.
**Acceptance:**
- `/api/gpus?active_only=true&exclude_flagged=true` returns only active+unflagged.
- `/api/gpus?active_only=false&exclude_flagged=false` includes all.
- No `use_active_avg` remains in `app.py`.

---

## T007 — Add the two toggles to GPU page
**Goal:** Frontend shows explicit toggles.
**File:** `SS-WEBSITE/templates/gpu.html`
**Steps:**
1. Find the filter bar container.
2. Replace the “Active-only averages” checkbox with two checkboxes:
   ```html
   <label><input type="checkbox" id="active-only" checked> Active listings only</label>
   <label><input type="checkbox" id="exclude-flagged" checked> Exclude flagged</label>
   ```
3. In the page's JS, read:
   ```javascript
   const activeOnly = document.getElementById('active-only').checked;
   const excludeFlagged = document.getElementById('exclude-flagged').checked;
   ```
4. Pass them as query params when calling `/api/gpus` and chart endpoints.
5. Persist them with `setSetting('active.gpu', activeOnly)` and `setSetting('flagged.gpu', excludeFlagged)`.
**Acceptance:**
- Two toggles visible on `/gpu`.
- Toggling changes the fetched data.
- Reload restores previous toggle state.

---

## T008 — Fix chart endpoints to exclude flagged and inactive
**Goal:** Charts are not skewed.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Edit `/api/gpu-performance-stats`: add flagged exclusion and inactive exclusion.
2. Edit `/api/ssd-statistics` and `/api/ssd-cost-per-gb-timeline`: add flagged exclusion.
3. Edit `/api/cpus` model stats subquery: add flagged exclusion.
4. Edit `/api/rams` market position CTE: add flagged + active-only default.
**SQL template:**
```sql
AND NOT EXISTS (SELECT 1 FROM flagged_listings fl WHERE fl.listing_id = l.listing_id)
AND l.is_active = true
```
**Acceptance:**
- Query results differ after adding the clauses (verify with a test category that has flagged/inactive rows).
- `/gpu` charts and `/ram` badges reflect the corrected data.

---

# Phase P2 — Shared Detail Modal

## T009 — Add showSharedListingDetail to base.html
**Goal:** One modal shell for all categories.
**File:** `SS-WEBSITE/templates/base.html`
**Steps:**
1. Add hidden modal HTML near the bottom of `<body>`:
   ```html
   <div id="shared-listing-modal" role="dialog" aria-modal="true" aria-labelledby="shared-modal-title" style="display:none;">
     <div id="shared-listing-backdrop"></div>
     <div id="shared-listing-content">
       <button id="shared-modal-close" aria-label="Close">×</button>
       <h2 id="shared-modal-title">Listing Detail</h2>
       <div id="shared-modal-body"></div>
     </div>
   </div>
   ```
2. Add base CSS variables:
   ```css
   --modal-bg: white;
   --modal-backdrop: rgba(0,0,0,0.5);
   --modal-box-bg: #f8f9fa;
   --modal-border: #eee;
   --modal-highlight-bg: #eff6ff;
   --modal-warn-bg: #fef3c7;
   --modal-muted-bg: #f3f4f6;
   ```
   plus dark overrides.
3. Add JS:
   ```javascript
   const detailSections = {};
   function registerDetailSection(category, fn) { detailSections[category] = fn; }
   function showSharedListingDetail(category, listingId) {
     fetch(`/api/detail/${category}/${listingId}`)
       .then(r => r.json())
       .then(data => {
         document.getElementById('shared-modal-title').textContent = data.listing.title || 'Listing Detail';
         const body = document.getElementById('shared-modal-body');
         body.innerHTML = '';
         if (detailSections[category]) {
           body.appendChild(detailSections[category](data));
         } else {
           body.innerHTML = '<p>No detail renderer registered for ' + category + '</p>';
         }
         openSharedModal();
       });
   }
   function openSharedModal() {
     const modal = document.getElementById('shared-listing-modal');
     modal.style.display = 'block';
     document.getElementById('shared-modal-close').focus();
     // focus trap, escape close handled separately
   }
   function closeSharedModal() {
     document.getElementById('shared-listing-modal').style.display = 'none';
   }
   document.getElementById('shared-modal-close').addEventListener('click', closeSharedModal);
   document.getElementById('shared-listing-backdrop').addEventListener('click', closeSharedModal);
   document.addEventListener('keydown', e => {
     if (e.key === 'Escape') closeSharedModal();
   });
   ```
**Acceptance:**
- A page can call `showSharedListingDetail('gpu', 123)` and a modal opens.
- Close button, backdrop click, and Escape all close it.
- Focus moves to the close button on open.

---

## T010 — Add /api/detail/<category>/<id> endpoint
**Goal:** One backend endpoint for modal data.
**File:** `SS-WEBSITE/app.py`
**Steps:**
1. Add route:
   ```python
   @app.route('/api/detail/<category>/<int:listing_id>')
   def api_detail(category, listing_id):
       # resolve table name from category
       table_map = {
           'gpu': 'listings', 'cpu': 'listings', 'ram': 'listings', 'ssd': 'listings',
           'motherboard': 'listings', 'monitor': 'listings', 'camera': 'listings',
           'console': 'listings', 'lens': 'listings', 'case': 'listings', 'psu': 'listings',
           'computer': 'listings'
       }
       # query by listing_id and category, fetch matched reference + price history
       # respect active/flagged toggles only for stats, not for the listing itself
       listing = ...
       matched = ...
       price_history = ...
       category_extras = compute_category_extras(category, listing)
       return jsonify({
           'listing': listing,
           'matched': matched,
           'price_history': price_history,
           'category_extras': category_extras
       })
   ```
2. Use existing repository functions where possible.
**Acceptance:**
- `curl /api/detail/gpu/123` returns the expected shape.
- Works for at least gpu, cpu, ram, ssd, monitor, lens.

---

## T011 — Migrate Monitors page to shared modal
**Goal:** Convert the existing reference page.
**File:** `SS-WEBSITE/templates/monitors.html`
**Steps:**
1. Remove inline modal HTML if any.
2. Register a monitor renderer:
   ```javascript
   registerDetailSection('monitor', data => {
     const div = document.createElement('div');
     div.innerHTML = `<p>Tier: ${data.category_extras.tier || 'N/A'}</p>` +
                     `<p>Size: ${data.listing.screen_size || ''}</p>` +
                     `<p>Resolution: ${data.listing.resolution || ''}</p>`;
     return div;
   });
   ```
3. Replace any `showSharedListingDetail` inline definition with the global one.
4. Ensure the row click calls `showSharedListingDetail('monitor', listingId)`.
**Acceptance:**
- `/monitors` still opens detail modals.
- Modal uses the shared markup in `base.html`.

---

## T012 — Migrate Motherboards page to shared modal
**Goal:** Replace bespoke modal.
**File:** `SS-WEBSITE/templates/motherboards.html`
**Steps:**
1. Find and remove the bespoke modal HTML + CSS + `showMotherboardDetail` function.
2. Register a `motherboard` detail renderer.
3. Change row clicks to call `showSharedListingDetail('motherboard', id)`.
4. After flagging inside the modal, refresh chipset/socket/model charts.
**Acceptance:**
- `/motherboards` detail modal works.
- Flagging inside the modal updates both the grid and the charts.

---

## T013 — Migrate Computers page to shared modal
**Goal:** Replace bespoke modal.
**File:** `SS-WEBSITE/templates/computers.html`
**Steps:**
1. Remove bespoke modal.
2. Register `computer` renderer showing prebuilt/build-type and component summary.
3. Fix `isPrebuilt` used-before-declaration if still present.
4. Row click → `showSharedListingDetail('computer', id)`.
**Acceptance:**
- `/computers` detail modal works.
- No JS errors from `isPrebuilt`.

---

## T014 — Migrate Consoles page to shared modal
**Goal:** Replace bespoke modal.
**File:** `SS-WEBSITE/templates/consoles.html`
**Steps:**
1. Remove bespoke modal.
2. Register `console` renderer.
3. Fix unflag endpoint to `/api/unflag-listing/<id>`.
4. Row click → `showSharedListingDetail('console', id)`.
**Acceptance:**
- `/consoles` detail modal works.
- Flag/unflag use canonical routes.

---

## T015 — Migrate Lenses page to shared modal
**Goal:** Replace bespoke modal.
**File:** `SS-WEBSITE/templates/lenses.html`
**Steps:**
1. Remove bespoke modal.
2. Register `lens` renderer showing brand, mount, focal length, aperture.
3. Move flagged-row exclusion from JS into `/api/lenses` SQL.
4. Row click → `showSharedListingDetail('lens', id)`.
**Acceptance:**
- `/lenses` detail modal works.
- Flagged rows are excluded server-side, not hidden with `display:none`.

---

# Phase P3 — Badge & Column Unification

## T016 — Create shared badge component
**Goal:** One helper for NEW/STEAL/UNICORN.
**File:** `SS-WEBSITE/templates/base.html`
**Steps:**
1. Add JS helper:
   ```javascript
   function renderBadges(priceStats, options = {}) {
     const overlay = options.overlay || false;
     const badges = [];
     if (priceStats.is_new) badges.push({ cls: 'badge-new', text: 'NEW', color: '#3b82f6' });
     if (priceStats.below_avg && priceStats.savings_pct >= 15 && !priceStats.is_new) {
       badges.push({ cls: 'badge-steal', text: 'STEAL', color: '#16a34a' });
     }
     if (priceStats.unicorn) badges.push({ cls: 'badge-unicorn', text: 'UNICORN', color: '#9333ea' });
     const container = document.createElement(overlay ? 'div' : 'span');
     container.className = overlay ? 'badge-overlay' : 'badge-row';
     badges.forEach(b => {
       const el = document.createElement('span');
       el.className = 'deal-badge ' + b.cls;
       el.textContent = b.text;
       el.style.background = b.color;
       container.appendChild(el);
     });
     return container;
   }
   ```
2. Add CSS for `.deal-badge`, `.badge-overlay`, `.badge-row`.
3. Remove GPU/CPU/Cases/PSU/Computers badge functions.
4. Delete FIRST/BUY logic and `discovered_*_models` keys.
**Acceptance:**
- GPU/CPU/Cases/PSU render identical badge markup.
- FIRST/BUY no longer appear.
- `discovered_gpu_models` and `discovered_cpu_models` are removed by migration.

---

## T017 — Unify column gear icon
**Goal:** Gear always in Actions header.
**File:** `SS-WEBSITE/templates/base.html` + all listing pages
**Steps:**
1. Add `renderColumnGear(tableId, columns, pageKey)` in `base.html`:
   - Render a gear icon inside the rightmost `<th>` of the Actions column.
   - Dropdown shows checkboxes for visibility and drag handles for order.
   - Persist to `ss_settings_v1.columns.<pageKey>`.
2. Update CPU page to use the shared function (it already has the right placement).
3. Update RAM page: remove separate gear column; move gear into Actions header.
4. Add gear to GPU, Motherboards, SSDs, PSUs, Cases, Lenses, Computers, Monitors, Consoles.
**Acceptance:**
- Gear icon is in the Actions header on every listing page.
- Column order/visibility persists.
- Required columns cannot be hidden.

---

# Phase P4 — Responsive & Accessibility

## T018 — Add prefers-reduced-motion guard
**Goal:** Stop animations for motion-sensitive users.
**File:** `SS-WEBSITE/templates/base.html`
**Steps:**
1. Add CSS:
   ```css
   @media (prefers-reduced-motion: reduce) {
     *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
     .unicorn-badge, .widget-card, .drag-clone { animation: none !important; }
   }
   ```
2. Add JS helper `prefersReducedMotion()`:
   ```javascript
   function prefersReducedMotion() {
     return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
   }
   ```
3. Pass `animation: !prefersReducedMotion()` to Chart.js configs and disable drag animation when true.
**Acceptance:**
- With OS reduced-motion enabled, UNICORN badge is static.
- Chart.js does not animate.

---

## T019 — Mobile navbar + 768 px breakpoint
**Goal:** Layout works down to 768 px.
**File:** `SS-WEBSITE/templates/base.html` + listing pages
**Steps:**
1. In `base.html` CSS:
   ```css
   @media (max-width: 900px) {
     .nav-links { display: none; }
     .nav-links.open { display: flex; flex-direction: column; }
     .nav-toggle { display: block; }
   }
   ```
2. Add a hamburger button that toggles `.nav-links.open`.
3. For listing pages, add:
   ```css
   @media (max-width: 768px) {
     .filters { flex-direction: column; align-items: stretch; }
     table.listings { display: none; }
     .listings-cards { display: block; }
     .listing-card { margin-bottom: 1rem; border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; }
   }
   ```
4. Add a card renderer per page that uses the same row data.
**Acceptance:**
- At 768 px, `/gpu` shows cards, filters stack vertically, nav is hamburger.
- Touch targets are at least 44×44 px.

---

## T020 — Modal and table accessibility
**Goal:** Keyboard and screen-reader friendly.
**File:** `SS-WEBSITE/templates/base.html` + listing pages
**Steps:**
1. In the shared modal JS, add focus trap:
   - On open, focus the close button.
   - Tab cycles through focusable elements inside the modal.
   - On close, return focus to the triggering element.
2. On every `<table>`, ensure `<th scope="col">`.
3. Add `aria-label` to sort buttons and filter toggles.
4. Add empty-state text that is not just visual.
**Acceptance:**
- Tab stays inside an open modal.
- Tables pass a quick Lighthouse accessibility check.

---

# Phase P5 — Performance & Cleanup

## T021 — Remove N+1 price-history fetches
**Goal:** Fetch history only in the detail modal.
**File:** `SS-WEBSITE/templates/psu.html` (and any other page doing per-row fetches)
**Steps:**
1. Find the block that does `Promise.all(listings.map(l => fetch('/api/price-history/' + l.listing_id)))`.
2. Delete it.
3. Ensure the detail modal gets history from `/api/detail/<category>/<id>`.
**Acceptance:**
- Network tab on `/psu` initial load shows zero `/api/price-history` calls.
- Opening a detail modal makes exactly one history request.

---

## T022 — Canonicalize flag endpoints
**Goal:** One flag route, one unflag route.
**File:** `SS-WEBSITE/app.py` + `admin.html` + `consoles.html`
**Steps:**
1. In `app.py`:
   - Keep `/api/flag-listing` and `/api/unflag-listing/<id>`.
   - Remove `/api/flag` and `/api/unflag` (or make them return 410).
2. Change payload field from `comment` to `reason` everywhere.
3. Update `admin.html` and `consoles.html` to use `/api/flag-listing` and `/api/unflag-listing/<id>`.
**Acceptance:**
- All flag/unflag traffic uses canonical routes.
- Payload field is `reason`.

---

## T023 — Delete dead badge/modal code
**Goal:** Remove duplicated or unreachable code.
**File:** `SS-WEBSITE/templates/cases.html` + `psu.html`
**Steps:**
1. In `cases.html`: remove duplicate `computeCaseDealBadges` and any unreachable badge insertion code.
2. In `psu.html`: remove references to undefined `showSharedListingDetail` if still present after T021.
**Acceptance:**
- No console errors about undefined functions.
- Dead code is removed.

---

# Phase P6 — Public Self-Hosting Mirror

## T024 — Provision the Linux server and install base services
**Goal:** A local Linux box is ready to host the public mirror.
**File:** `SS-WEBSITE/docs/project_wiki.md` (Section 17) + server config notes
**Steps:**
1. Install Ubuntu/Debian LTS on the target machine (or VM).
2. Install required packages:
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib nginx git python3 python3-venv python3-pip rsync openssh-server
   ```
3. Create service user:
   ```bash
   sudo useradd -r -m -s /bin/bash ssmarket
   sudo mkdir -p /srv/ss-market/{app,images,backups,venv,scripts}
   sudo chown -R ssmarket:ssmarket /srv/ss-market
   ```
4. Configure PostgreSQL user and database:
   ```bash
   sudo -u postgres psql -c "CREATE USER ssmarket WITH PASSWORD 'replace-me';"
   sudo -u postgres psql -c "CREATE DATABASE ss_market OWNER ssmarket;"
   ```
**Acceptance:**
- `systemctl status postgresql` and `systemctl status nginx` are active.
- `sudo -u ssmarket psql -U ssmarket -d ss_market -c "SELECT 1;"` works.

## T025 — Create one-command database sync from Windows
**Goal:** Run one PowerShell command to copy the local DB to the mirror.
**File:** `sync_to_mirror.ps1` (repo root)
**Steps:**
1. Create `G:\Github\SS-WEB-SCRAPPER\sync_to_mirror.ps1`:
   ```powershell
   param(
     [string]$RemoteHost = "ss-mirror.local",
     [string]$RemoteUser = "ssmarket",
     [string]$DumpFile = "ss_market_latest.dump"
   )
   $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
   $DumpPath = Join-Path $RepoRoot $DumpFile
   Write-Host "Dumping local database..."
   & pg_dump -h localhost -p 5433 -U crawler -d ss_market -Fc -f $DumpPath
   if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
   Write-Host "Uploading to mirror..."
   & scp $DumpPath "${RemoteUser}@${RemoteHost}:/srv/ss-market/backups/"
   Write-Host "Restoring remote database..."
   & ssh "${RemoteUser}@${RemoteHost}" "sudo /srv/ss-market/scripts/restore_db.sh /srv/ss-market/backups/${DumpFile}"
   Write-Host "Restarting remote web service..."
   & ssh "${RemoteUser}@${RemoteHost}" "sudo systemctl restart ss-website"
   Write-Host "Sync complete."
   ```
2. Create remote restore script `/srv/ss-market/scripts/restore_db.sh`:
   ```bash
   #!/bin/bash
   set -e
   DUMP="$1"
   sudo -u postgres pg_dropdatabase --if-exists ss_market_temp || true
   sudo -u postgres createdb -O ssmarket ss_market_temp
   sudo -u ssmarket pg_restore -d ss_market_temp "$DUMP"
   sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='ss_market';"
   sudo -u postgres psql -c "DROP DATABASE IF EXISTS ss_market_old;"
   sudo -u postgres psql -c "ALTER DATABASE ss_market RENAME TO ss_market_old;"
   sudo -u postgres psql -c "ALTER DATABASE ss_market_temp RENAME TO ss_market;"
   ```
3. Make the script executable.
**Acceptance:**
- `powershell -File sync_to_mirror.ps1` completes without errors.
- The remote database reflects the latest local data.

## T026 — Set up push-to-deploy for the website
**Goal:** `git push mirror main` deploys the latest website.
**File:** `SS-WEBSITE/docs/project_wiki.md` (Section 17.3)
**Steps:**
1. On the Linux server, create a bare repo:
   ```bash
   sudo mkdir -p /srv/git
   sudo git init --bare /srv/git/SS-WEB-SCRAPPER.git
   sudo chown -R ssmarket:ssmarket /srv/git/SS-WEB-SCRAPPER.git
   ```
2. Add the post-receive hook `/srv/git/SS-WEB-SCRAPPER.git/hooks/post-receive`:
   ```bash
   #!/bin/bash
   GIT_WORK_TREE=/srv/ss-market/app git checkout -f main
   cd /srv/ss-market/app/SS-WEBSITE
   source /srv/ss-market/venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart ss-website
   ```
3. On Windows, add the remote:
   ```powershell
   git remote add mirror ssh://ssmarket@ss-mirror.local:2222/srv/git/SS-WEB-SCRAPPER.git
   ```
4. Push:
   ```powershell
   git push mirror main
   ```
**Acceptance:**
- Pushing triggers checkout, dependency install, and service restart.
- The public URL shows the new code within 30 seconds.

## T027 — Configure systemd + nginx for production
**Goal:** The public site runs reliably behind nginx.
**File:** server config files (add to repo under `SS-WEBSITE/deploy/`)
**Steps:**
1. Create `SS-WEBSITE/deploy/ss-website.service`:
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
   Environment="DATABASE_PASSWORD=replace-me"
   Environment="IMAGES_ROOT=/srv/ss-market/images"
   ExecStart=/srv/ss-market/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. Create `SS-WEBSITE/deploy/nginx.conf`:
   ```nginx
   server {
       listen 80;
       server_name ss-mirror.local;

       location /static/ { alias /srv/ss-market/app/SS-WEBSITE/static/; }
       location /images/ { alias /srv/ss-market/images/; }

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```
3. Symlink and enable:
   ```bash
   sudo cp /srv/ss-market/app/SS-WEBSITE/deploy/ss-website.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ss-website
   sudo ln -s /srv/ss-market/app/SS-WEBSITE/deploy/nginx.conf /etc/nginx/sites-enabled/ss-website
   sudo nginx -t && sudo systemctl restart nginx
   ```
**Acceptance:**
- `systemctl status ss-website` shows active.
- `curl http://ss-mirror.local/api/stats` returns JSON.

## T028 — Sync images and decide scraper location
**Goal:** Public images are available; decide whether Linux also scrapes.
**File:** `sync_images.ps1` (repo root)
**Steps:**
1. Create `sync_images.ps1`:
   ```powershell
   param(
     [string]$RemoteHost = "ss-mirror.local",
     [string]$RemoteUser = "ssmarket"
   )
   $Images = "G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\images"
   & rsync -avz --delete "$Images/" "${RemoteUser}@${RemoteHost}:/srv/ss-market/images/"
   ```
2. Run after `sync_to_mirror.ps1` when needed, or add as a final step.
3. Document the decision in `project_wiki.md` Section 17.5.
**Acceptance:**
- `/images/<category>/<file>` loads from the public server.
- Wiki records whether scraping is Windows-only or also Linux.

# Phase P7 — Scale

## T029 — Server-side component filters for Computers
**Goal:** `/computers` filters work with pagination.
**File:** `SS-WEBSITE/app.py` + `SS-WEBSITE/templates/computers.html`
**Steps:**
1. In `/api/computers`, accept query params: `cpu_brand`, `gpu_brand`, `ram_min`, `ram_max`, `ssd_min`, `prebuilt`, `active_only`, `exclude_flagged`.
2. Apply them in SQL.
3. In `computers.html`, send filters as query params and remove client-side filtering.
4. Update `/api/computers/stats` to accept and apply the same filters.
**Acceptance:**
- Filtering works with 10,000+ listings without client-side lag.
- Stats panel reflects current filters.
- URL is shareable.

## T030 — Add backend pagination to GPU/CPU
**Goal:** Paginate large inventories.
**File:** `SS-WEBSITE/app.py` + `SS-WEBSITE/templates/gpu.html` + `cpu.html`
**Steps:**
1. In `/api/gpus` and `/api/cpus`, accept `page`, `per_page` (default 50), `sort`, `order`.
2. Return `{listings: [...], total, page, per_page}`.
3. In frontend, add pagination controls and keep filters applied.
**Acceptance:**
- `/api/gpus?page=2&per_page=50` returns the correct slice.
- Pagination controls work and preserve filters.

## T031 — Define API response envelope
**Goal:** Consistent success/error format.
**File:** `SS-WEBSITE/app.py` + `SS-WEBSITE/templates/base.html`
**Steps:**
1. Add helpers:
   ```python
   def success_response(data, meta=None):
       return jsonify({'success': True, 'data': data, 'meta': meta or {}})

   def error_response(code, message, status_code=400):
       return jsonify({'success': False, 'error': {'code': code, 'message': message}}), status_code
   ```
2. Add `apiRequest()` in `base.html`:
   ```javascript
   async function apiRequest(url, options = {}) {
     const res = await fetch(url, options);
     const data = await res.json().catch(() => ({}));
     if (!res.ok) {
       showToast(data.error?.message || 'Request failed', 'error');
       throw new Error(data.error?.message || 'Request failed');
     }
     return data;
   }
   ```
3. Migrate GPU endpoints first as the reference page.
**Acceptance:**
- GPU endpoints return the envelope.
- Shared wrapper shows toast on error.

---

# Quick-start checklist

Start here in order:
1. T001 + T002 + T003 — auth layer
2. T004 — settings registry
3. T005 — price_stats contract
4. T006 + T007 + T008 — active/flagged
5. T009 + T010 + T011 — shared modal
6. T016 + T017 — badge/column unification
7. T018 + T019 + T020 — responsive/a11y
8. T021 + T022 + T023 — cleanup
9. T024 + T025 + T026 + T027 + T028 — self-hosting mirror
10. T029 + T030 + T031 — scale
# Quick-start checklist

Start here in order:
1. T001 + T002 + T003 — auth layer
2. T004 — settings registry
3. T005 — price_stats contract
4. T006 + T007 + T008 — active/flagged
5. T009 + T010 + T011 — shared modal
6. T016 + T017 — badge/column unification
7. T018 + T019 + T020 — responsive/a11y
8. T021 + T022 + T023 — cleanup
9. T024 + T025 + T026 — scale
