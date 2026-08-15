"""Replace the content block of ram.html with a modern, cleaner UI."""
from pathlib import Path
import re

FILE = Path(r"G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\ram.html")
text = FILE.read_text(encoding="utf-8")

new_content = '''{% block content %}
<div class="ram-page">

    <!-- ========== TOP STATS: 4 compact cards ========== -->
    <div class="ram-stats-row">
        <div class="ram-stat-card ddr4">
            <div class="stat-head">
                <span>DDR4 — Active market</span>
                <span class="dot"></span>
            </div>
            <div class="stat-main"><span id="stat-ddr4-active">—</span></div>
            <div class="stat-sub"><span id="stat-ddr4-avg">€— avg</span> · <span id="stat-ddr4-median">€— median</span></div>
            <div class="stat-bar"><div id="stat-ddr4-bar" style="width: 0%"></div></div>
        </div>
        <div class="ram-stat-card ddr3">
            <div class="stat-head"><span>DDR3</span><span class="dot"></span></div>
            <div class="stat-main"><span id="stat-ddr3-active">—</span></div>
            <div class="stat-sub"><span id="stat-ddr3-avg">€— avg</span></div>
            <div class="stat-bar"><div id="stat-ddr3-bar" style="width: 0%"></div></div>
        </div>
        <div class="ram-stat-card ddr5">
            <div class="stat-head"><span>DDR5</span><span class="dot"></span></div>
            <div class="stat-main"><span id="stat-ddr5-active">—</span></div>
            <div class="stat-sub"><span id="stat-ddr5-avg">€— avg</span></div>
            <div class="stat-bar"><div id="stat-ddr5-bar" style="width: 0%"></div></div>
        </div>
        <div class="ram-stat-card" style="--accent: var(--ram-text-dim);">
            <div class="stat-head"><span>Total</span><span class="dot" style="background: var(--ram-text-dim);"></span></div>
            <div class="stat-main"><span id="stat-total">—</span></div>
            <div class="stat-sub"><span id="stat-active">— active</span> · <span id="stat-avg-price">€—</span></div>
        </div>
    </div>

    <!-- ========== CAPACITY MINI-GRID ========== -->
    <div class="ram-cap-grid" id="ram-cap-grid">
        <!-- Filled by JS, but with skeleton placeholders for layout -->
        <div class="ram-cap-card" data-cap="4">
            <div class="cap-label">4 GB</div>
            <div class="cap-prices" id="cap-4-prices">
                <div class="cap-ddr"><span class="ddr-dot d3"></span>DDR3 <span class="count" id="cap-4-d3">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d4"></span>DDR4 <span class="count" id="cap-4-d4">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d5"></span>DDR5 <span class="count" id="cap-4-d5">—</span></div>
            </div>
        </div>
        <div class="ram-cap-card" data-cap="8">
            <div class="cap-label">8 GB</div>
            <div class="cap-prices">
                <div class="cap-ddr"><span class="ddr-dot d3"></span>DDR3 <span class="count" id="cap-8-d3">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d4"></span>DDR4 <span class="count" id="cap-8-d4">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d5"></span>DDR5 <span class="count" id="cap-8-d5">—</span></div>
            </div>
        </div>
        <div class="ram-cap-card" data-cap="16">
            <div class="cap-label">16 GB</div>
            <div class="cap-prices">
                <div class="cap-ddr"><span class="ddr-dot d3"></span>DDR3 <span class="count" id="cap-16-d3">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d4"></span>DDR4 <span class="count" id="cap-16-d4">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d5"></span>DDR5 <span class="count" id="cap-16-d5">—</span></div>
            </div>
        </div>
        <div class="ram-cap-card" data-cap="32">
            <div class="cap-label">32 GB</div>
            <div class="cap-prices">
                <div class="cap-ddr"><span class="ddr-dot d3"></span>DDR3 <span class="count" id="cap-32-d3">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d4"></span>DDR4 <span class="count" id="cap-32-d4">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d5"></span>DDR5 <span class="count" id="cap-32-d5">—</span></div>
            </div>
        </div>
        <div class="ram-cap-card" data-cap="64">
            <div class="cap-label">64 GB+</div>
            <div class="cap-prices">
                <div class="cap-ddr"><span class="ddr-dot d3"></span>DDR3 <span class="count" id="cap-64-d3">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d4"></span>DDR4 <span class="count" id="cap-64-d4">—</span></div>
                <div class="cap-ddr"><span class="ddr-dot d5"></span>DDR5 <span class="count" id="cap-64-d5">—</span></div>
            </div>
        </div>
    </div>

    <!-- ========== CHARTS ROW ========== -->
    <div class="ram-charts-row">
        <div class="ram-chart-card">
            <h3>Avg Price by DDR Type</h3>
            <div class="chart-container"><canvas id="avgPriceByDDRChart"></canvas></div>
        </div>
        <div class="ram-chart-card">
            <h3>Capacity Distribution</h3>
            <div class="chart-container"><canvas id="capacityDistChart"></canvas></div>
        </div>
    </div>

    <!-- ========== TOP DEALS STRIP ========== -->
    <div class="ram-deals-strip" id="top-deals-section" style="display: none;">
        <h3>🔥 Top deals — price ≥ 15% below model average</h3>
        <div class="ram-deals-grid" id="top-deals-container"></div>
    </div>

    <!-- ========== AVG PRICE OVER TIME ========== -->
    <div class="ram-chart-card full" style="margin-bottom: 1rem;">
        <h3 style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem;">
            <span>Avg RAM Price by Capacity &amp; Type over Time</span>
            <span class="period-btns">
                <button id="ram-avg-week" class="active" onclick="setRAMAvgPeriod('week')">Week</button>
                <button id="ram-avg-month" onclick="setRAMAvgPeriod('month')">Month</button>
            </span>
        </h3>
        <div class="chart-container" style="height: 260px;">
            <canvas id="ramAvgPriceChart"></canvas>
        </div>
    </div>

    <!-- ========== FILTER BAR ========== -->
    <div class="ram-filterbar">
        <div class="filter-chips" role="group" aria-label="Toggles">
            <button class="active" data-toggle="active" onclick="toggleFilterPill(this, 'active')">Active only</button>
            <button data-toggle="conf" onclick="toggleFilterPill(this, 'conf')">High conf ≥70%</button>
            <button data-toggle="allavg" onclick="toggleFilterPill(this, 'allavg')">All RAM avgs</button>
        </div>

        <div class="divider"></div>

        <div class="filter-group">
            <span class="filter-label">DDR</span>
            <div class="filter-chips" id="ddr-filter-chips">
                <button class="active" data-ddr="all" onclick="filterByDDR('all', this)">All</button>
                <button data-ddr="DDR3" onclick="filterByDDR('DDR3', this)">DDR3</button>
                <button data-ddr="DDR4" onclick="filterByDDR('DDR4', this)">DDR4</button>
                <button data-ddr="DDR5" onclick="filterByDDR('DDR5', this)">DDR5</button>
            </div>
        </div>

        <div class="filter-group">
            <span class="filter-label">Capacity</span>
            <select id="capacity-filter" onchange="loadListings()">
                <option value="all">All</option>
                <option value="4">4 GB</option>
                <option value="8">8 GB</option>
                <option value="16">16 GB</option>
                <option value="32">32 GB</option>
                <option value="64">64 GB+</option>
            </select>
        </div>

        <div class="filter-group">
            <span class="filter-label">Sort</span>
            <select id="sort-by" onchange="loadListings()">
                <option value="date_posted">Date</option>
                <option value="price">Price</option>
            </select>
            <select id="sort-order" onchange="loadListings()">
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
            </select>
        </div>

        <div class="filter-group">
            <span class="filter-label">RAM ID</span>
            <input type="text" id="ram-id-filter" class="ram-id-input" placeholder="e.g. 189"
                   onchange="loadListings()" onkeyup="if(event.key==='Enter') loadListings()">
        </div>

        <button class="export-btn" onclick="exportToCSV()">📥 Export CSV</button>
    </div>

    <!-- ========== LISTINGS TABLE ========== -->
    <div class="ram-listings" id="listings-container">
        <div class="ram-loading">Loading RAM listings…</div>
    </div>

    <!-- ========== PRICE TRENDS ========== -->
    <div class="ram-trends">
        <h3>
            <span>📈 Price trends</span>
            <span style="display: inline-flex; gap: 0.5rem; align-items: center;">
                <span class="filter-label">Capacity</span>
                <select id="trend-capacity" onchange="updatePriceTrends()">
                    <option value="8">8 GB</option>
                    <option value="16" selected>16 GB</option>
                    <option value="32">32 GB</option>
                </select>
                <span class="filter-label">DDR</span>
                <select id="trend-ddr" onchange="updatePriceTrends()">
                    <option value="all">All</option>
                    <option value="DDR4" selected>DDR4</option>
                    <option value="DDR5">DDR5</option>
                </select>
            </span>
        </h3>
        <div class="chart-container" style="height: 260px;">
            <canvas id="priceTrendChart"></canvas>
        </div>
    </div>

</div>

<!-- Model History Popup Container -->
<div id="model-history-popup" style="display: none;"></div>
{% endblock %}'''

new_text = re.sub(
    r'\{% block content %\}.*?\{% endblock %\}',
    new_content,
    text,
    count=1,
    flags=re.DOTALL,
)
print(f"Content replaced. Was {len(text)} chars, now {len(new_text)} chars")
FILE.write_text(new_text, encoding="utf-8")
print("Done")
