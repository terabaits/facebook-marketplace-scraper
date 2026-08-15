# -*- coding: utf-8 -*-
"""Redesign the computers.html listings page to match the RAM page UI patterns."""
from pathlib import Path

FILE = Path(r"G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\computers.html")
text = FILE.read_text(encoding="utf-8")

# ---------- 1. Replace the main filter bar ----------
old_filter_bar = '''        <div class="filters">
            <label>
                <input type="checkbox" id="active-only" checked onchange="loadComputers()">
                Active only
            </label>
            <label>
                <input type="checkbox" id="prebuilt-only" onchange="loadComputers()">
                Prebuilt only
            </label>
            <label>
                <input type="checkbox" id="hide-prebuilt" onchange="loadComputers()">
                Hide Prebuilt
            </label>
            <label>
                <input type="checkbox" id="admin-mark-prebuilt" class="hidden" onchange="toggleAdminMarkMode()">
                <span id="admin-mark-label" class="hidden">Mark Prebuilt Mode</span>
            </label>
            <label>
                Sort:
                <select id="sort-by" onchange="loadComputers()">
                    <option value="date_posted">{{ t('Date Posted') }}</option>
                    <option value="price">{{ t('Price') }}</option>
                    <option value="score">Performance Score</option>
                    <option value="value_score">Value Score</option>
                </select>
            </label>
            <label>
                Order:
                <select id="sort-order" onchange="loadComputers()">
                    <option value="desc">{{ t('Descending') }}</option>
                    <option value="asc">{{ t('Ascending') }}</option>
                </select>
            </label>
            <button class="btn btn-primary" onclick="openAddListingModal()">➕ Add Listing</button>
        </div>'''

new_filter_bar = '''        <div class="comp-filterbar">
            <div class="filter-chips" role="group" aria-label="Toggles">
                <button class="active" id="toggle-active" data-toggle="active" onclick="toggleComputerPill(this, 'active')">Active only</button>
                <button id="toggle-prebuilt" data-toggle="prebuilt" onclick="toggleComputerPill(this, 'prebuilt')">Prebuilt only</button>
                <button id="toggle-hide-prebuilt" data-toggle="hide-prebuilt" onclick="toggleComputerPill(this, 'hidePrebuilt')">Hide prebuilt</button>
                <button id="toggle-admin-mark" data-toggle="admin-mark" class="hidden" onclick="toggleComputerPill(this, 'adminMark')">Mark prebuilt</button>
            </div>

            <div class="divider"></div>

            <div class="filter-group">
                <span class="filter-label">Sort</span>
                <select id="sort-by" onchange="loadComputers()">
                    <option value="date_posted">{{ t('Date Posted') }}</option>
                    <option value="price">{{ t('Price') }}</option>
                    <option value="score">Performance Score</option>
                    <option value="value_score">Value Score</option>
                </select>
                <select id="sort-order" onchange="loadComputers()">
                    <option value="desc">{{ t('Descending') }}</option>
                    <option value="asc">{{ t('Ascending') }}</option>
                </select>
            </div>

            <button class="export-btn" onclick="openAddListingModal()">➕ Add Listing</button>
        </div>'''

if old_filter_bar in text:
    text = text.replace(old_filter_bar, new_filter_bar)
    print("Replaced main filter bar with pill toggles")
else:
    print("WARNING: main filter bar pattern not found")

# ---------- 2. Update loadComputers() ----------
old_load_head = '''    const activeOnly = document.getElementById('active-only').checked;
    const prebuiltOnly = document.getElementById('prebuilt-only').checked;
    const hidePrebuilt = document.getElementById('hide-prebuilt').checked;
    const sortBy = document.getElementById('sort-by').value;
    const sortOrder = document.getElementById('sort-order').value;'''

new_load_head = '''    const activeOnly = document.getElementById('toggle-active') ? document.getElementById('toggle-active').classList.contains('on') : true;
    const prebuiltOnly = document.getElementById('toggle-prebuilt') ? document.getElementById('toggle-prebuilt').classList.contains('on') : false;
    const hidePrebuilt = document.getElementById('toggle-hide-prebuilt') ? document.getElementById('toggle-hide-prebuilt').classList.contains('on') : false;
    const sortBy = document.getElementById('sort-by').value;
    const sortOrder = document.getElementById('sort-order').value;'''

if old_load_head in text:
    text = text.replace(old_load_head, new_load_head)
    print("Updated loadComputers() to use new pill toggles")

# ---------- 3. Add helper functions before loadComputers ----------
insertion_point = "async function loadComputers() {"
helper_functions = '''// Strip the SS.COM category breadcrumb from a raw listing title
function cleanComputerTitle(title) {
    if (!title) return '';
    let t = String(title)
        .replace(/^Datori un orgtehnika\\s*[\\/\\-]?\\s*Datori[,\\s]+Cena\\s*\\d+\\s*[\\u20ac\\u20bd\\$]\\.?\\s*/i, '')
        .replace(/^Datori un orgtehnika\\s*[\\/\\-]?\\s*Dat[ao]ri\\s*[\\/\\-]?\\s*P[\\u0101a]rdod\\s*/i, '')
        .replace(/^Datori un orgtehnika\\s*[\\/\\-]?\\s*/i, '')
        .replace(/\\s*-\\s*Sludin\\u0101jumi\\s*$/i, '')
        .replace(/\\s*-\\s*Sludinajumi\\s*$/i, '')
        .trim();
    return t;
}

// Pill toggle handler for the main filter bar
function toggleComputerPill(btn, key) {
    const isOn = btn.classList.toggle('on');
    btn.classList.toggle('active', isOn);
    if (key === 'adminMark') {
        toggleAdminMarkMode();
        if (!isOn) {
            btn.classList.toggle('on', isAdminMode());
        }
    }
    loadComputers();
}

'''
if insertion_point in text and "function cleanComputerTitle" not in text:
    text = text.replace(insertion_point, helper_functions + insertion_point, 1)
    print("Added cleanComputerTitle() + toggleComputerPill() helpers")

# ---------- 4. Replace the table header ----------
old_thead = '''                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Title</th>
                        <th>{{ t('Type') }}</th>
                        <th>{{ t('Price') }}</th>
                        <th>Components</th>
                        <th>Score</th>
                        <th>Location</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>'''
new_thead = '''                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Listing</th>
                        <th>{{ t('Price') }}</th>
                        <th>Components</th>
                        <th>Score</th>
                        <th>Location</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>'''
if old_thead in text:
    text = text.replace(old_thead, new_thead)
    print("Removed 'Type' column from table header")

# ---------- 5. Replace the components block ----------
# Use real Unicode chars (the file has them)
old_components_block = '''            // Build components summary
            let components = [];
            if (item.cpu_name) {
                const cpuProducer = item.cpu_producer || '';
                const cpuName = cpuProducer && item.cpu_name.toLowerCase().startsWith(cpuProducer.toLowerCase()) ? item.cpu_name : `${cpuProducer} ${item.cpu_name}`.trim();
                components.push(`<span class="badge badge-cpu">CPU: ${cpuName}</span>`);
            }
            if (item.gpu_model) {
                components.push(`<span class="badge badge-gpu">GPU: ${item.gpu_vendor || ''} ${item.gpu_model}</span>`);
            }
            let ramCapacity = item.ram_capacity;
            if (!ramCapacity && item.ram_match_method) {
                const ramMatch = item.ram_match_method.match(/(\\d+)\\s*GB/i);
                if (ramMatch) ramCapacity = parseInt(ramMatch[1]);
            }
            let ramType = item.ram_type;
            if (!ramType && item.ram_match_method) {
                const ddrMatch = item.ram_match_method.match(/ddr(\\d)/i);
                if (ddrMatch) ramType = `DDR${ddrMatch[1]}`;
            }
            if (ramCapacity) {
                components.push(`<span class="badge badge-ram" data-ram-capacity="${ramCapacity}" data-ram-type="${ramType || ''}">RAM: ${ramCapacity}GB ${ramType || ''}</span>`);
            }
            let ssdCapacity = item.ssd_capacity;
            if (!ssdCapacity && item.ssd_match_method) {
                const ssdMatch = item.ssd_match_method.match(/(\\d+)\\s*GB/i);
                if (ssdMatch) ssdCapacity = parseInt(ssdMatch[1]);
            }
            if (ssdCapacity) {
                components.push(`<span class="badge badge-ssd">SSD: ${ssdCapacity}GB</span>`);
            } else if (item.ssd_match_method && !['none', 'null', ''].includes(item.ssd_match_method.toLowerCase().trim())) {
                components.push(`<span class="badge badge-ssd">SSD: detected</span>`);
            }
            if (item.prebuilt_badge) {
                components.push(item.prebuilt_badge);
            } else if (isPrebuilt) {
                components.push(`<span class="badge" style="background: #e74c3c; color: white;">\U0001F3ED Prebuilt</span>`);
            }

            const componentsHtml = components.length > 0 ? components.join('<br>') : '<em class="no-components">No components detected</em>';

            const pcType = item.pc_type || (isPrebuilt ? 'prebuilt' : 'custom');'''

new_components_block = '''            // Build components summary (2-column grid: CPU+GPU top, RAM+SSD bottom)
            let compCpu = '', compGpu = '', compRam = '', compSsd = '';
            if (item.cpu_name) {
                const cpuProducer = item.cpu_producer || '';
                const cpuName = cpuProducer && item.cpu_name.toLowerCase().startsWith(cpuProducer.toLowerCase()) ? item.cpu_name : `${cpuProducer} ${item.cpu_name}`.trim();
                compCpu = `<div class="comp-row"><span class="comp-tag comp-cpu">CPU</span><span class="comp-name">${cpuName}</span></div>`;
            }
            if (item.gpu_model) {
                compGpu = `<div class="comp-row"><span class="comp-tag comp-gpu">GPU</span><span class="comp-name">${item.gpu_vendor || ''} ${item.gpu_model}</span></div>`;
            }
            let ramCapacity = item.ram_capacity;
            if (!ramCapacity && item.ram_match_method) {
                const ramMatch = item.ram_match_method.match(/(\\d+)\\s*GB/i);
                if (ramMatch) ramCapacity = parseInt(ramMatch[1]);
            }
            let ramType = item.ram_type;
            if (!ramType && item.ram_match_method) {
                const ddrMatch = item.ram_match_method.match(/ddr(\\d)/i);
                if (ddrMatch) ramType = `DDR${ddrMatch[1]}`;
            }
            if (ramCapacity) {
                compRam = `<div class="comp-row"><span class="comp-tag comp-ram">RAM</span><span class="comp-name">${ramCapacity}GB ${ramType || ''}</span></div>`;
            }
            let ssdCapacity = item.ssd_capacity;
            if (!ssdCapacity && item.ssd_match_method) {
                const ssdMatch = item.ssd_match_method.match(/(\\d+)\\s*GB/i);
                if (ssdMatch) ssdCapacity = parseInt(ssdMatch[1]);
            }
            if (ssdCapacity) {
                compSsd = `<div class="comp-row"><span class="comp-tag comp-ssd">SSD</span><span class="comp-name">${ssdCapacity}GB</span></div>`;
            } else if (item.ssd_match_method && !['none', 'null', ''].includes(item.ssd_match_method.toLowerCase().trim())) {
                compSsd = `<div class="comp-row"><span class="comp-tag comp-ssd">SSD</span><span class="comp-name">detected</span></div>`;
            }
            const anyComp = compCpu || compGpu || compRam || compSsd;
            const componentsHtml = anyComp
                ? `<div class="comp-grid">${compCpu}${compGpu}${compRam}${compSsd}</div>`
                : '<em class="no-components">No components detected</em>';

            const pcType = item.pc_type || (isPrebuilt ? 'prebuilt' : 'custom');
            const pcTypeChip = isPrebuilt
                ? '<span class="pc-type-chip prebuilt">\U0001F3ED Prebuilt</span>'
                : '<span class="pc-type-chip custom">\U0001F6E0 Custom</span>';
            const cleanTitle = cleanComputerTitle(item.title) || (isPrebuilt ? 'Prebuilt PC' : 'Custom PC');'''

if old_components_block in text:
    text = text.replace(old_components_block, new_components_block)
    print("Replaced components renderer (2-column grid + PC type chip + cleaned title)")
else:
    print("WARNING: components block pattern not found")

# ---------- 6. Replace the row body ----------
old_row = '''            html += `
                <tr class="clickable ${pcType}-row" data-pc-type="${pcType}" onclick="showComputerDetail('${safeListingId}')">
                    <td class="listing-image-cell">${imageHtml}</td>
                    <td>
                        <strong>${item.title}</strong>${item.prebuilt_badge ? `<span class="badge" style="background: #e74c3c; color: white; margin-left: 0.4rem;">${item.prebuilt_badge}</span>` : ''}
                        ${isAdminMode() && item.is_prebuilt ? `<button class="btn btn-tiny" onclick="event.stopPropagation(); unmarkPrebuilt('${safeListingId}')" title="Unmark as prebuilt">✕</button>` : ''}
                    </td>
                    <td>${pcType}</td>
                    <td><span class="price">€${item.price_eur}</span></td>
                    <td>${componentsHtml}</td>
                    <td>
                        ${item.performance_score ? `<span class="badge" style="background:#3498db;color:#fff;" title="Performance score: CPU 40%, GPU 40%, RAM 10%, SSD 10%">⚡ ${item.performance_score.toLocaleString()}</span>` : ''}
                        ${item.value_score ? `<span class="badge" style="background:#2ecc71;color:#fff;" title="Value score = performance / price">💎 ${item.value_score.toFixed(2)}</span>` : ''}
                    </td>
                    <td>${item.seller_location || 'N/A'}</td>
                    <td>${item.date_posted ? new Date(item.date_posted).toLocaleDateString() : 'N/A'}</td>
                    <td>
                        <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); showComputerDetail('${safeListingId}')">{{ t('Details') }}</button>
                        <a href="${item.listing_url || '#' }" target="_blank" class="btn btn-small" onclick="event.stopPropagation()">View →</a>
                    </td>
                </tr>
            `;'''

new_row = '''            html += `
                <tr class="clickable ${pcType}-row" data-pc-type="${pcType}" onclick="showComputerDetail('${safeListingId}')">
                    <td class="listing-image-cell">${imageHtml}</td>
                    <td>
                        <div class="comp-cell-name">
                            <div class="comp-title-row">
                                <span class="comp-title">${cleanTitle}</span>
                                ${pcTypeChip}
                            </div>
                            ${isAdminMode() && item.is_prebuilt ? `<button class="btn btn-tiny" onclick="event.stopPropagation(); unmarkPrebuilt('${safeListingId}')" title="Unmark as prebuilt">✕</button>` : ''}
                        </div>
                    </td>
                    <td><span class="comp-price">€${item.price_eur}</span>${item.price_difference_eur < 0 ? `<div class="comp-price-sub">−€${Math.abs(item.price_difference_eur).toFixed(0)} below parts</div>` : ''}</td>
                    <td>${componentsHtml}</td>
                    <td>
                        <div class="comp-scores">
                            ${item.performance_score ? `<span class="comp-score perf" title="Performance score: CPU 40%, GPU 40%, RAM 10%, SSD 10%">⚡ ${item.performance_score.toFixed(1)}</span>` : ''}
                            ${item.value_score ? `<span class="comp-score value" title="Value score = performance / price">💎 ${item.value_score.toFixed(2)}</span>` : ''}
                        </div>
                    </td>
                    <td><span class="comp-meta">${item.seller_location || '—'}</span></td>
                    <td><span class="comp-meta">${item.date_posted ? new Date(item.date_posted).toLocaleDateString('en-GB', {day:'2-digit',month:'short'}) : '—'}</span></td>
                    <td class="comp-actions">
                        <button class="comp-action-btn" title="View details" onclick="event.stopPropagation(); showComputerDetail('${safeListingId}')">📄</button>
                        <a href="${item.listing_url || '#'}" target="_blank" class="comp-action-btn" title="Open listing" onclick="event.stopPropagation()">↗</a>
                    </td>
                </tr>
            `;'''

if old_row in text:
    text = text.replace(old_row, new_row)
    print("Replaced row body with new structure (cleaned title, icon-only actions)")
else:
    print("WARNING: row body pattern not found")

# ---------- 7. Add new CSS at the end ----------
new_css = '''<style>
/* ===== Computers page UI: modern filter bar + cells ===== */
:root {
    --comp-primary: #6366f1;
    --comp-primary-soft: #818cf8;
    --comp-text: var(--text-color, #1e293b);
    --comp-text-dim: var(--text-dim, #64748b);
    --comp-border: var(--card-border, rgba(0,0,0,0.08));
    --comp-bg: var(--card-bg, #ffffff);
    --comp-bg-soft: var(--section-bg, #f8fafc);
    --comp-shadow: 0 1px 2px rgba(0,0,0,0.04);
    --comp-radius: 10px;
    --comp-radius-sm: 6px;
}
[data-theme="dark"] {
    --comp-border: rgba(255,255,255,0.08);
    --comp-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.comp-filterbar {
    background: var(--comp-bg);
    border: 1px solid var(--comp-border);
    border-radius: var(--comp-radius);
    padding: 0.75rem 1rem;
    box-shadow: var(--comp-shadow);
    margin-bottom: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
}
.comp-filterbar .filter-chips {
    display: flex;
    gap: 0.25rem;
    border: 1px solid var(--comp-border);
    border-radius: 8px;
    padding: 2px;
    background: var(--comp-bg-soft);
}
.comp-filterbar .filter-chips button {
    background: transparent;
    border: none;
    color: var(--comp-text-dim);
    padding: 0.3rem 0.65rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
}
.comp-filterbar .filter-chips button:hover {
    background: var(--comp-bg);
    color: var(--comp-text);
}
.comp-filterbar .filter-chips button.active,
.comp-filterbar .filter-chips button.on {
    background: var(--comp-primary);
    color: white;
}
.comp-filterbar .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.comp-filterbar .filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--comp-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.comp-filterbar select, .comp-filterbar input[type="text"] {
    background: var(--comp-bg-soft);
    border: 1px solid var(--comp-border);
    color: var(--comp-text);
    border-radius: 6px;
    padding: 0.35rem 0.6rem;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
}
.comp-filterbar .divider {
    width: 1px;
    height: 22px;
    background: var(--comp-border);
    margin: 0 0.25rem;
}
.comp-filterbar .export-btn {
    margin-left: auto;
    background: var(--comp-primary);
    color: white;
    border: none;
    padding: 0.45rem 0.95rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    transition: all 0.15s;
}
.comp-filterbar .export-btn:hover {
    background: #4f46e5;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(99, 102, 241, 0.25);
}

.comp-cell-name {
    min-width: 200px;
}
.comp-cell-name .comp-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}
.comp-cell-name .comp-title {
    font-weight: 600;
    color: var(--comp-text);
    font-size: 0.9rem;
    line-height: 1.3;
}
.pc-type-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
}
.pc-type-chip.prebuilt {
    background: #fee2e2;
    color: #b91c1c;
}
.pc-type-chip.custom {
    background: #dbeafe;
    color: #1d4ed8;
}
[data-theme="dark"] .pc-type-chip.prebuilt {
    background: rgba(239,68,68,0.2);
    color: #fca5a5;
}
[data-theme="dark"] .pc-type-chip.custom {
    background: rgba(59,130,246,0.2);
    color: #93c5fd;
}

.comp-price {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--comp-text);
}
.comp-price-sub {
    font-size: 0.7rem;
    color: #10b981;
    font-weight: 600;
    margin-top: 0.1rem;
}

.comp-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.25rem 0.6rem;
    min-width: 240px;
}
.comp-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    line-height: 1.3;
    min-width: 0;
}
.comp-tag {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    color: white;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    flex-shrink: 0;
    min-width: 28px;
    text-align: center;
}
.comp-tag.comp-cpu { background: #667eea; }
.comp-tag.comp-gpu { background: #764ba2; }
.comp-tag.comp-ram { background: #27ae60; }
.comp-tag.comp-ssd { background: #3498db; }
.comp-name {
    color: var(--comp-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
}
.no-components {
    color: var(--comp-text-dim);
    font-size: 0.8rem;
    font-style: italic;
}

.comp-scores {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.comp-score {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    white-space: nowrap;
    color: white;
}
.comp-score.perf { background: #3498db; }
.comp-score.value { background: #2ecc71; }

.comp-meta {
    font-size: 0.8rem;
    color: var(--comp-text);
}

.comp-actions {
    white-space: nowrap;
    text-align: right;
}
.comp-action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: 1px solid var(--comp-border);
    background: var(--comp-bg-soft);
    color: var(--comp-text-dim);
    border-radius: 6px;
    cursor: pointer;
    margin-left: 0.2rem;
    transition: all 0.15s;
    font-size: 0.85rem;
    text-decoration: none;
}
.comp-action-btn:hover {
    background: var(--comp-primary);
    color: white;
    border-color: var(--comp-primary);
}

/* Hide the old inline badges that used .badge inside the listing table (we use comp-* now) */
.clickable .badge { display: none; }
</style>'''

text = text.rstrip() + '\n\n' + new_css
print("Added new CSS block at end of file")

FILE.write_text(text, encoding="utf-8")
print(f"\nDone. New file size: {len(text)} chars")
