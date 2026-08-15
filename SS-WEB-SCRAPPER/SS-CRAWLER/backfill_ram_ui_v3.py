"""Update the JS in ram.html to match the new HTML structure."""
from pathlib import Path
import re

FILE = Path(r"G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\ram.html")
text = FILE.read_text(encoding="utf-8")

# Replace the loadStats function (line ~1215) to also populate the DDR-specific cards
new_load_stats = '''async function loadStats() {
    try {
        const response = await fetch('/api/rams/stats');
        const data = await response.json();
        const stats = data.success ? data.stats : (data.total_listings !== undefined ? data : null);
        if (!stats) {
            console.error('Stats response format:', data);
            return;
        }
        // Top-level totals
        const totalEl = document.getElementById('stat-total');
        const activeEl = document.getElementById('stat-active');
        const avgEl = document.getElementById('stat-avg-price');
        if (totalEl) totalEl.textContent = stats.total_listings || 0;
        if (activeEl) activeEl.textContent = stats.active_listings || 0;
        if (avgEl) avgEl.textContent = '€' + (parseFloat(stats.avg_price) || 0).toFixed(2);

        // Per-DDR cards (if backend returns by_ddr)
        if (stats.by_ddr) {
            ['DDR3', 'DDR4', 'DDR5'].forEach(type => {
                const d = stats.by_ddr[type] || {};
                const key = type.toLowerCase();
                const activeEl = document.getElementById('stat-' + key + '-active');
                const avgEl = document.getElementById('stat-' + key + '-avg');
                const medEl = document.getElementById('stat-' + key + '-median');
                const barEl = document.getElementById('stat-' + key + '-bar');
                if (activeEl) activeEl.textContent = d.active || 0;
                if (avgEl) avgEl.textContent = '€' + (parseFloat(d.avg) || 0).toFixed(0) + ' avg';
                if (medEl) medEl.textContent = '€' + (parseFloat(d.median) || 0).toFixed(0) + ' median';
                if (barEl && stats.total_active) {
                    const pct = Math.min(100, ((d.active || 0) / stats.total_active) * 100);
                    barEl.style.width = pct.toFixed(1) + '%';
                }
            });
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}'''
text = re.sub(
    r'async function loadStats\(\) \{.*?\n\}',
    new_load_stats,
    text,
    count=1,
    flags=re.DOTALL,
)
print("Replaced loadStats")

# Replace updateDDRStats and updateCapacityCards with a single function that updates the new grid
old_ddr_stats_block = '''// Update DDR type stats cards
function updateDDRStats(listings) {
    // Group by DDR type
    const ddrData = {
        'DDR3': { count: 0, prices: [], sizes: {} },
        'DDR4': { count: 0, prices: [], sizes: {} },
        'DDR5': { count: 0, prices: [], sizes: {} }
    };

    listings.forEach(item => {
        const ddrType = item.ddr_type || item.ram_type || 'DDR4';
        if (!ddrData[ddrType]) return;

        ddrData[ddrType].count++;
        ddrData[ddrType].prices.push(item.price_eur || 0);

        // Track sizes
        const capacity = item.capacity_gb || 0;
        if (capacity > 0) {
            if (!ddrData[ddrType].sizes[capacity]) {
                ddrData[ddrType].sizes[capacity] = [];
            }
            ddrData[ddrType].sizes[capacity].push(item.price_eur || 0);
        }
    });

    // Update each card
    ['DDR3', 'DDR4', 'DDR5'].forEach(type => {
        const data = ddrData[type];
        const countEl = document.getElementById(type.toLowerCase() + '-count');
        const pricesEl = document.getElementById(type.toLowerCase() + '-prices');

        if (countEl) {
            countEl.textContent = data.count;
        }

        if (pricesEl) {
            if (data.count === 0) {
                pricesEl.innerHTML = '<div style="opacity: 0.7;">No data</div>';
            } else {
                // Calculate avg price per size (e.g., "32GB - €90")
                const sizePrices = Object.entries(data.sizes).map(([size, prices]) => {
                    const sizeAvg = prices.reduce((a, b) => a + b, 0) / prices.length;
                    return { size: parseInt(size), avgPrice: sizeAvg, count: prices.length };
                }).sort((a, b) => a.size - b.size);

                // Format: "4GB - €45, 8GB - €60, 16GB - €85, 32GB - €150"
                const priceList = sizePrices.map(s =>
                    `${s.size}GB - €${s.avgPrice.toFixed(0)}`
                ).join('<br>');

                pricesEl.innerHTML = priceList || 'No size data';
            }
        }
    });

    // Update capacity cards (DDR type x size breakdown)
    updateCapacityCards(listings);
}

// Update capacity cards with DDR type x size breakdown
function updateCapacityCards(listings) {
    // Structure: { size: { DDR3: avgPrice, DDR4: avgPrice, DDR5: avgPrice } }
    const capacityData = {
        4: {}, 8: {}, 16: {}, 32: {}, 64: {}
    };

    listings.forEach(item => {
        const capacity = item.capacity_gb || 0;
        const ddrType = item.ddr_type || item.ram_type || 'DDR4';

        if (capacityData[capacity] && item.price_eur > 0) {
            if (!capacityData[capacity][ddrType]) {
                capacityData[capacity][ddrType] = [];
            }
            capacityData[capacity][ddrType].push(item.price_eur);
        }
    });

    // Update each capacity card
    [4, 8, 16, 32, 64].forEach(size => {
        ['DDR3', 'DDR4', 'DDR5'].forEach(ddrType => {
            const el = document.getElementById(`${ddrType.toLowerCase()}-${size}gb-price`);
            if (el) {
                const prices = capacityData[size][ddrType];
                if (prices && prices.length > 0) {
                    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
                    el.innerHTML = `€${avg.toFixed(0)} (${prices.length})`;
                } else {
                    el.innerHTML = '-';
                    el.style.opacity = '0.5';
                }
            }
        });
    });
}'''

new_ddr_stats_block = '''// Update DDR-specific top stats (active count, avg, median, bar)
function updateDDRStats(listings) {
    const ddrData = { 'DDR3': { count: 0, prices: [] }, 'DDR4': { count: 0, prices: [] }, 'DDR5': { count: 0, prices: [] } };
    listings.forEach(item => {
        const t = item.ddr_type || item.ram_type;
        if (!ddrData[t]) return;
        ddrData[t].count++;
        if (item.price_eur > 0) ddrData[t].prices.push(item.price_eur);
    });
    const totalActive = listings.filter(i => i.is_active !== false).length || 1;
    ['DDR3', 'DDR4', 'DDR5'].forEach(type => {
        const d = ddrData[type];
        const key = type.toLowerCase();
        const activeEl = document.getElementById('stat-' + key + '-active');
        const avgEl = document.getElementById('stat-' + key + '-avg');
        const medEl = document.getElementById('stat-' + key + '-median');
        const barEl = document.getElementById('stat-' + key + '-bar');
        if (activeEl) activeEl.textContent = d.count;
        if (avgEl) avgEl.textContent = d.prices.length ? '€' + (d.prices.reduce((a,b)=>a+b,0)/d.prices.length).toFixed(0) + ' avg' : '€— avg';
        if (medEl) {
            const sorted = [...d.prices].sort((a,b)=>a-b);
            const med = sorted.length ? sorted[Math.floor(sorted.length/2)] : 0;
            medEl.textContent = sorted.length ? '€' + med.toFixed(0) + ' median' : '€— median';
        }
        if (barEl) barEl.style.width = Math.min(100, (d.count / totalActive) * 100).toFixed(1) + '%';
    });
    updateCapacityGrid(listings);
}

// Update capacity grid: per-capacity card shows count per DDR type
function updateCapacityGrid(listings) {
    // bucket: { cap: { ddr: count } }
    const buckets = {};
    listings.forEach(item => {
        let cap = item.capacity_gb || 0;
        if (cap >= 64) cap = 64;
        const t = item.ddr_type || item.ram_type;
        if (!buckets[cap]) buckets[cap] = {};
        if (t) buckets[cap][t] = (buckets[cap][t] || 0) + 1;
    });
    [4, 8, 16, 32, 64].forEach(cap => {
        ['d3', 'd4', 'd5'].forEach((dk, i) => {
            const type = ['DDR3', 'DDR4', 'DDR5'][i];
            const el = document.getElementById('cap-' + cap + '-' + dk);
            if (el) el.textContent = buckets[cap] && buckets[cap][type] ? buckets[cap][type] : '—';
        });
    });
    // Make capacity cards clickable to filter
    document.querySelectorAll('.ram-cap-card').forEach(card => {
        card.onclick = () => {
            const cap = card.dataset.cap;
            const sel = document.getElementById('capacity-filter');
            if (sel) {
                sel.value = cap === '64' ? '64' : cap;
                loadListings();
            }
        };
    });
}'''

text = text.replace(old_ddr_stats_block, new_ddr_stats_block)
print("Replaced updateDDRStats + updateCapacityCards")

# Replace filterByDDR to accept button element
old_filter_by_ddr = '''function filterByDDR(ddrType) {
    currentDDRFilter = ddrType;
    loadListings();
}'''
new_filter_by_ddr = '''function filterByDDR(ddrType, btn) {
    currentDDRFilter = ddrType;
    // Update chip active state
    document.querySelectorAll('#ddr-filter-chips button').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadListings();
}'''
text = text.replace(old_filter_by_ddr, new_filter_by_ddr)
print("Replaced filterByDDR")

# Replace toggleAllRAMAvg with the new toggleFilterPill
old_toggle_all_avg = '''function toggleAllRAMAvg() {
    const checkbox = document.getElementById('all-ram-avg');
    useAllRAMsForStats = checkbox?.checked || false;
    if (useAllRAMsForStats) {
        loadAllRAMsForStats().then(() => loadListings());
    } else {
        loadListings();
    }
}'''
new_toggle_pill = '''// New pill toggle handler: toggles "on" class on the pill and updates state
function toggleFilterPill(btn, key) {
    const isOn = btn.classList.toggle('on');
    if (key === 'active') useActiveOnly = isOn;
    else if (key === 'conf') useHighConfidence = isOn;
    else if (key === 'allavg') {
        useAllRAMsForStats = isOn;
        if (useAllRAMsForStats) {
            loadAllRAMsForStats().then(() => loadListings());
            return;
        }
    }
    loadListings();
}

// Legacy shim for any remaining code that still calls toggleAllRAMAvg
function toggleAllRAMAvg() {
    useAllRAMsForStats = !useAllRAMsForStats;
    const btn = document.querySelector('[data-toggle="allavg"]');
    if (btn) btn.classList.toggle('on', useAllRAMsForStats);
    if (useAllRAMsForStats) loadAllRAMsForStats().then(() => loadListings());
    else loadListings();
}'''
text = text.replace(old_toggle_all_avg, new_toggle_pill)
print("Replaced toggleAllRAMAvg with toggleFilterPill")

# Update loadListings to use the new toggle state
old_load_active = '''    const activeOnly = document.getElementById('active-only').checked;
    const highConfidence = document.getElementById('high-confidence').checked;'''
new_load_active = '''    const activeOnly = useActiveOnly;
    const highConfidence = useHighConfidence;'''
text = text.replace(old_load_active, new_load_active)
print("Updated loadListings active/high conf")

# Add the useActiveOnly/useHighConfidence globals at the top of the script
text = text.replace(
    'let allRAMs = [];\nlet allRAMsForStats = [];\nlet useAllRAMsForStats = false;',
    'let allRAMs = [];\nlet allRAMsForStats = [];\nlet useAllRAMsForStats = false;\nlet useActiveOnly = true;       // toggled by filter pill\nlet useHighConfidence = false;   // toggled by filter pill',
    1
)
print("Added toggle state globals")

# Update setRAMAvgPeriod to use the new .active class instead of inline style
old_set_period = '''function setRAMAvgPeriod(period) {
    ramAvgPeriod = period;
    document.getElementById('ram-avg-week').style.background = period === 'week' ? 'var(--accent-color)' : '';
    document.getElementById('ram-avg-week').style.color = period === 'week' ? 'white' : '';
    document.getElementById('ram-avg-month').style.background = period === 'month' ? 'var(--accent-color)' : '';
    document.getElementById('ram-avg-month').style.color = period === 'month' ? 'white' : '';
    updateRAMAvgPriceChart(allRAMsForStats);
}'''
new_set_period = '''function setRAMAvgPeriod(period) {
    ramAvgPeriod = period;
    const weekBtn = document.getElementById('ram-avg-week');
    const monthBtn = document.getElementById('ram-avg-month');
    if (weekBtn) weekBtn.classList.toggle('active', period === 'week');
    if (monthBtn) monthBtn.classList.toggle('active', period === 'month');
    updateRAMAvgPriceChart(allRAMsForStats);
}'''
text = text.replace(old_set_period, new_set_period)
print("Replaced setRAMAvgPeriod")

# Update renderTopDeals to use the new ram-deal-card HTML
old_render_top_deals = '''    const html = deals.map(item => {
        const imageUrl = item.local_image_path ? `/images/${item.local_image_path}` : item.image_url;
        const savingsAbs = (parseFloat(item.price_stats.avg) - parseFloat(item.price_eur)).toFixed(0);
        const pricePerGB = item.capacity_gb ? (item.price_eur / item.capacity_gb).toFixed(2) : '0.00';
        return `
            <div style="display: flex; gap: 1rem; align-items: center; padding: 0.75rem; background: rgba(220,38,38,0.05); border: 1px solid rgba(220,38,38,0.2); border-radius: 10px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';" onmouseout="this.style.transform=''; this.style.boxShadow='';" onclick="showSharedListingDetail('${item.listing_id}', true)">
                <div style="flex-shrink: 0;">
                    ${imageUrl ? `<img src="${imageUrl}" alt="RAM" style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; border: 1px solid #eee;">` : '<div style="width: 70px; height: 70px; border-radius: 8px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #999; font-size: 1.5rem;">📷</div>'}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 700; font-size: 1rem; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.ram_name || 'Unknown RAM'}</div>
                    <div style="font-size: 0.875rem; color: #666; margin-top: 0.25rem;">
                        ${item.ddr_type || item.ram_type || 'Unknown'} · ${item.capacity_gb || '?'}GB · ${item.speed || ''}
                    </div>
                    <div style="font-size: 0.8rem; color: #888; margin-top: 0.25rem;">
                        ${item.seller_location || 'N/A'} · ${item.date_posted ? new Date(item.date_posted).toLocaleDateString() : 'N/A'}
                    </div>
                </div>
                <div style="text-align: right; flex-shrink: 0;">
                    <div style="font-size: 1.25rem; font-weight: 800; color: #dc2626;">€${Number(item.price_eur).toFixed(2)}</div>
                    <div style="font-size: 0.875rem; color: #666; text-decoration: line-through;">avg €${item.price_stats.avg}</div>
                    <div style="font-size: 0.8rem; color: #16a34a; font-weight: 700;">▼ €${savingsAbs} (${item.savingsPct.toFixed(0)}%)</div>
                    <div style="font-size: 0.75rem; color: #888;">€${pricePerGB}/GB</div>
                </div>
            </div>
        `;
    }).join('');'''
new_render_top_deals = '''    const html = deals.map(item => {
        const imageUrl = item.local_image_path ? `/images/${item.local_image_path}` : item.image_url;
        const savingsAbs = (parseFloat(item.price_stats.avg) - parseFloat(item.price_eur)).toFixed(0);
        const pricePerGB = item.capacity_gb ? (item.price_eur / item.capacity_gb).toFixed(2) : '0.00';
        return `
            <div class="ram-deal-card" onclick="showSharedListingDetail('${item.listing_id}', true)">
                ${imageUrl
                    ? `<img class="deal-img" src="${imageUrl}" alt="RAM">`
                    : `<div class="deal-img">📷</div>`}
                <div class="deal-info">
                    <div class="deal-name">${item.ram_name || 'Unknown RAM'}</div>
                    <div class="deal-meta">${item.ddr_type || item.ram_type || 'Unknown'} · ${item.capacity_gb || '?'}GB · ${item.speed || ''}</div>
                    <div class="deal-meta">${item.seller_location || 'N/A'} · ${item.date_posted ? new Date(item.date_posted).toLocaleDateString() : 'N/A'}</div>
                </div>
                <div class="deal-price">
                    <div class="deal-price-main">€${Number(item.price_eur).toFixed(0)}</div>
                    <div class="deal-avg">avg €${item.price_stats.avg}</div>
                    <div class="deal-save">−€${savingsAbs} (${item.savingsPct.toFixed(0)}%)</div>
                    <div class="deal-meta">€${pricePerGB}/GB</div>
                </div>
            </div>
        `;
    }).join('');'''
text = text.replace(old_render_top_deals, new_render_top_deals)
print("Replaced renderTopDeals")

# Update the table row renderer to use the new cell classes
old_row_renderer = '''        // DDR badge - handle null/undefined safely
        let ddrType = item.ddr_type || item.ram_type || 'DDR4';
        if (!ddrType && item.speed) {
            const speedStr = String(item.speed);
            if (speedStr.includes('DDR3')) ddrType = 'DDR3';
            else if (speedStr.includes('DDR5')) ddrType = 'DDR5';
            else ddrType = 'DDR4';
        }
        ddrType = ddrType || 'DDR4';
        const ddrColors = { 'DDR2': '#95a5a6', 'DDR3': '#e74c3c', 'DDR4': '#3498db', 'DDR5': '#9b59b6' };
        const ddrBadge = `<span class="badge" style="background: ${ddrColors[ddrType] || '#667eea'}; color: white;">${ddrType}</span>`;'''
new_row_renderer = '''        // DDR detection
        let ddrType = item.ddr_type || item.ram_type || 'DDR4';
        if (!ddrType && item.speed) {
            const speedStr = String(item.speed);
            if (speedStr.includes('DDR3')) ddrType = 'DDR3';
            else if (speedStr.includes('DDR5')) ddrType = 'DDR5';
            else ddrType = 'DDR4';
        }
        ddrType = ddrType || 'DDR4';
        const ddrCls = ddrType === 'DDR3' ? 'd3' : ddrType === 'DDR4' ? 'd4' : ddrType === 'DDR5' ? 'd5' : '';'''
text = text.replace(old_row_renderer, new_row_renderer)
print("Updated row DDR detection")

# Replace the price cell renderer to use the new structure
old_price_cell = '''            case 'col-price':
                return `<td data-col="col-price" ${style}><span class="${priceClass}">€${Number(item.price_eur).toFixed(2)}</span><br><small>€${pricePerGB}/GB</small>${priceIndicator ? `<br><small>${priceIndicator}</small>` : ''}</td>`;'''
new_price_cell = '''            case 'col-price': {
                const belowClass = item.price_stats && item.price_stats.below_avg ? 'below' : (item.price_stats ? 'above' : '');
                const tag = item.price_stats && item.price_stats.below_avg
                    ? '<span class="price-tag below">↓ below avg</span>'
                    : (item.price_stats ? '<span class="price-tag above">↑ above avg</span>' : '');
                return `<td data-col="col-price" ${style}>
                    <div class="ram-cell-price">
                        <div class="price-main ${belowClass}">€${Number(item.price_eur).toFixed(0)}</div>
                        <div class="price-meta"><span class="price-pg">€${pricePerGB}/GB</span>${tag}</div>
                    </div>
                </td>`;
            }'''
text = text.replace(old_price_cell, new_price_cell)
print("Replaced price cell")

# Replace the RAM name cell renderer
old_name_cell = '''            case 'col-ram':
                return `<td data-col="col-ram" ${style}><strong>${item.ram_name || 'Unknown RAM'}</strong><br>${ddrBadge} ${item.capacity_gb}GB ${item.speed ? `<br><small>${item.speed}</small>` : ''}<br><small class="${confidenceClass}">${(confidence*100).toFixed(0)}% confidence</small></td>`;'''
new_name_cell = '''            case 'col-ram': {
                const confPct = Math.round(confidence * 100);
                const confCls = confPct >= 70 ? 'high' : confPct >= 50 ? 'medium' : 'low';
                return `<td data-col="col-ram" ${style}>
                    <div class="ram-cell-name">
                        <div class="ram-title">${item.ram_name || 'Unknown RAM'}</div>
                        <div class="ram-attrs">
                            <span class="ddr-chip ${ddrCls}">${ddrType}</span>
                            <span class="cap-chip">${item.capacity_gb || '?'} GB</span>
                            ${item.speed ? `<span class="speed-text">${item.speed}</span>` : ''}
                        </div>
                        <div class="conf-bar">
                            <div class="conf-bar-track"><div class="conf-bar-fill ${confCls}" style="width: ${confPct}%"></div></div>
                            <span class="conf-label">${confPct}%</span>
                        </div>
                    </div>
                </td>`;
            }'''
text = text.replace(old_name_cell, new_name_cell)
print("Replaced name cell")

# Replace the model position cell renderer
old_model_cell = '''            case 'col-model':
                return `<td data-col="col-model" ${style}>${item.is_unicorn ? `<span class="unicorn-badge" title="Only one listing of this RAM model in all history!">🦄 UNICORN</span>` : (item.price_stats ? `<div style="font-size: 0.875rem;">Avg: €${item.price_stats.avg}<br>Range: €${item.price_stats.min} - €${item.price_stats.max}</div><div class="price-bar"><div class="price-bar-fill" style="width: ${item.price_stats.percentile}%"></div></div><small>${item.price_stats.percentile}% percentile</small>` : 'N/A')}</td>`;'''
new_model_cell = '''            case 'col-model':
                if (item.is_unicorn) {
                    return `<td data-col="col-model" ${style}><span class="ram-action-btn" style="width:auto;padding:0 8px;background:linear-gradient(135deg,#a855f7,#ec4899);color:white;font-weight:700;font-size:0.7rem;">🦄 UNICORN</span></td>`;
                }
                if (!item.price_stats) return `<td data-col="col-model" ${style}><span class="ram-cell-meta">—</span></td>`;
                return `<td data-col="col-model" ${style}>
                    <div class="ram-cell-stat">
                        <div class="stat-head">Model avg</div>
                        <div class="stat-value">€${item.price_stats.avg}</div>
                        <div class="stat-range">€${item.price_stats.min}–€${item.price_stats.max}</div>
                        <div class="stat-bar"><div style="width: ${item.price_stats.percentile}%"></div></div>
                        <div class="stat-pct"><span class="pct-num">${item.price_stats.percentile}%</span> percentile</div>
                    </div>
                </td>`;'''
text = text.replace(old_model_cell, new_model_cell)
print("Replaced model position cell")

# Replace the market position cell renderer
old_market_cell = '''            case 'col-market':
                return `<td data-col="col-market" ${style}>${item.ddr_stats ? `<div style="font-size: 0.875rem;">${item.ddr_stats.ddr_type} ${item.ddr_stats.capacity_gb}GB<br>Avg: €${item.ddr_stats.avg}<br>Range: €${item.ddr_stats.min} - €${item.ddr_stats.max}</div><div class="price-bar"><div class="price-bar-fill" style="width: ${item.ddr_stats.percentile}%"></div></div><small>${item.ddr_stats.percentile}% percentile</small>` : 'N/A')}</td>`;'''
new_market_cell = '''            case 'col-market':
                if (!item.ddr_stats) return `<td data-col="col-market" ${style}><span class="ram-cell-meta">—</span></td>`;
                return `<td data-col="col-market" ${style}>
                    <div class="ram-cell-stat">
                        <div class="stat-head">${item.ddr_stats.ddr_type} ${item.ddr_stats.capacity_gb}GB</div>
                        <div class="stat-value">€${item.ddr_stats.avg}</div>
                        <div class="stat-range">€${item.ddr_stats.min}–€${item.ddr_stats.max}</div>
                        <div class="stat-bar"><div style="width: ${item.ddr_stats.percentile}%"></div></div>
                        <div class="stat-pct"><span class="pct-num">${item.ddr_stats.percentile}%</span> percentile</div>
                    </div>
                </td>`;'''
text = text.replace(old_market_cell, new_market_cell)
print("Replaced market position cell")

# Replace the image cell renderer
old_image_cell = '''            case 'col-image':
                const ramDealBadges = buildRamDealBadges(item);
                const ramImageOverlay = ramDealBadges
                    ? `<div style="position: absolute; top: 35px; left: 4px; display: flex; flex-direction: column; gap: 4px; z-index: 10; align-items: flex-start;">${ramDealBadges}</div>`
                    : '';
                return `<td data-col="col-image" ${style} style="position: relative;">${ramImageOverlay}${imageUrl ? `<img src="${imageUrl}" alt="RAM" class="listing-thumb" loading="lazy" onclick="event.stopPropagation(); showImageModal('${imageClickUrl}', 'RAM')">` : '<div class="listing-thumb-placeholder">📷</div>'}</td>`;'''
new_image_cell = '''            case 'col-image': {
                const isSteal = item.price_stats && item.price_stats.below_avg
                    && ((parseFloat(item.price_stats.avg) - item.price_eur) / parseFloat(item.price_stats.avg)) >= 0.15;
                const isNew = item.is_new === true;
                const isUnicorn = item.is_unicorn;
                const badgeStack = (isSteal || isNew || isUnicorn) ? `
                    <div class="deal-badge-stack">
                        ${isSteal ? '<span class="badge steal" title="Price ≥15% below model average">🔥 STEAL</span>' : ''}
                        ${isUnicorn ? '<span class="badge unicorn" title="Only one listing of this model in all history">🦄</span>' : ''}
                        ${isNew && !isSteal ? '<span class="badge is-new" title="New in latest import">🆕 NEW</span>' : ''}
                    </div>` : '';
                const imgContent = imageUrl
                    ? `<img src="${imageUrl}" alt="RAM" loading="lazy" onclick="event.stopPropagation(); showImageModal('${imageClickUrl}', 'RAM')">`
                    : '<div class="placeholder-img">📷</div>';
                return `<td data-col="col-image" class="ram-cell-image" ${style}>${badgeStack}${imgContent}</td>`;
            }'''
text = text.replace(old_image_cell, new_image_cell)
print("Replaced image cell")

# Replace the latency cell renderer
old_latency_cell = '''            case 'col-latency':
                return `<td data-col="col-latency" ${style}>${item.cas_latency || 'N/A'}</td>`;'''
new_latency_cell = '''            case 'col-latency': {
                const lat = item.cas_latency;
                if (!lat || lat === 'N/A') {
                    return `<td data-col="col-latency" ${style}><span class="ram-cell-latency empty">—</span></td>`;
                }
                return `<td data-col="col-latency" ${style}><span class="ram-cell-latency">CL${lat}</span></td>`;
            }'''
text = text.replace(old_latency_cell, new_latency_cell)
print("Replaced latency cell")

# Replace the location cell renderer
old_location_cell = '''            case 'col-location':
                return `<td data-col="col-location" ${style}>${item.seller_location || 'N/A'}</td>`;'''
new_location_cell = '''            case 'col-location': {
                const loc = item.seller_location || '—';
                return `<td data-col="col-location" ${style}><span class="ram-cell-meta">${loc}</span></td>`;
            }'''
text = text.replace(old_location_cell, new_location_cell)
print("Replaced location cell")

# Replace the date cell renderer
old_date_cell = '''            case 'col-date':
                return `<td data-col="col-date" ${style}>${dateStr}</td>`;'''
new_date_cell = '''            case 'col-date': {
                const d = new Date(item.date_posted);
                const dStr = !isNaN(d.getTime()) && d.getFullYear() > 2000
                    ? d.toLocaleDateString('en-GB', {day: '2-digit', month: 'short'})
                    : '—';
                return `<td data-col="col-date" ${style}><span class="ram-cell-meta">${dStr}</span></td>`;
            }'''
text = text.replace(old_date_cell, new_date_cell)
print("Replaced date cell")

# Replace the actions cell renderer (icon-only buttons with tooltips)
old_actions_cell = '''            case 'col-actions':
                return `<td data-col="col-actions" ${style}><button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); showSharedListingDetail('${item.listing_id}', true)">History</button><button class="btn btn-small" style="background: #9b59b6; margin-left: 0.25rem;" onmouseover="showModelHistoryPopup(event, '${item.listing_id}')" onmouseout="hideModelHistoryPopup()" onclick="event.stopPropagation(); showSharedListingDetail('${item.listing_id}', true)">ℹ️ Info</button><button class="btn btn-small" style="background: #dc3545; color: white; margin-left: 0.25rem;" onclick="event.stopPropagation(); showFlagModalWithCategories('${item.listing_id.replace(/'/g, "\\\\'").replace(/"/g, '&quot;')}', '${(item.ram_name || item.name || 'Unknown RAM').replace(/'/g, "\\\\'").replace(/"/g, '&quot;')}')">🚩 Flag</button><a href="${item.listing_url}" target="_blank" class="btn btn-small" onclick="event.stopPropagation()" style="margin-left: 0.25rem;">View →</a></td>`;'''
new_actions_cell = '''            case 'col-actions': {
                const safeId = (item.listing_id || '').replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
                const safeName = (item.ram_name || 'Unknown RAM').replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
                return `<td data-col="col-actions" class="ram-cell-actions" ${style}>
                    <button class="ram-action-btn" title="View history" onclick="event.stopPropagation(); showSharedListingDetail('${item.listing_id}', true)">📋</button>
                    <button class="ram-action-btn" title="Model info" onmouseover="showModelHistoryPopup(event, '${item.listing_id}')" onmouseout="hideModelHistoryPopup()" onclick="event.stopPropagation(); showSharedListingDetail('${item.listing_id}', true)">ℹ️</button>
                    <button class="ram-action-btn flag" title="Flag listing" onclick="event.stopPropagation(); showFlagModalWithCategories('${safeId}', '${safeName}')">🚩</button>
                    <a href="${item.listing_url}" target="_blank" class="ram-action-btn" title="Open listing" onclick="event.stopPropagation()">↗</a>
                </td>`;
            }'''
text = text.replace(old_actions_cell, new_actions_cell)
print("Replaced actions cell")

# Update the summary row to use the new style
old_summary = '''        html += `
            <tfoot id="summary-row" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: bold;">
                <tr>
                    <td colspan="${summaryColspan}" style="text-align: right; padding: 0.75rem;">Summary:</td>
                    <td style="padding: 0.75rem;">€${totalPrice.toFixed(2)} total</td>
                    <td style="padding: 0.75rem; font-size: 0.85rem;">avg: €${avgPrice.toFixed(2)}</td>
                    <td style="padding: 0.75rem;" colspan="${visibleCols - summaryColspan - 2}">${listings.length} listings shown</td>
                </tr>
            </tfoot>`;'''
new_summary = '''        html += `
            <tfoot class="ram-summary-row">
                <tr>
                    <td class="summary-label">Summary</td>
                    <td class="summary-amount">€${totalPrice.toFixed(0)}</td>
                    <td class="summary-count">avg €${avgPrice.toFixed(2)}</td>
                    <td class="summary-count" colspan="${Math.max(1, visibleCols - 3)}">${listings.length} listings</td>
                </tr>
            </tfoot>`;'''
text = text.replace(old_summary, new_summary)
print("Replaced summary row")

FILE.write_text(text, encoding="utf-8")
print(f"Done. Final file: {len(text)} chars")
