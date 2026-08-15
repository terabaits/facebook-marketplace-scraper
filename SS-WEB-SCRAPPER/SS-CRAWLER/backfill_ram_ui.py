"""Replace the CSS block and content block of ram.html with a modern redesign."""
from pathlib import Path

FILE = Path(r"G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\ram.html")
text = FILE.read_text(encoding="utf-8")

# New CSS block (replaces lines 5-346)
new_css = '''{% block extra_css %}
<style>
:root {
    --ram-primary: #6366f1;
    --ram-primary-soft: #818cf8;
    --ram-success: #10b981;
    --ram-warning: #f59e0b;
    --ram-error: #ef4444;
    --ram-text: var(--text-color, #1e293b);
    --ram-text-dim: var(--text-dim, #64748b);
    --ram-border: var(--card-border, rgba(255,255,255,0.08));
    --ram-bg: var(--card-bg, #ffffff);
    --ram-bg-soft: #f8fafc;
    --ram-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06);
    --ram-shadow-lg: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.05);
    --ram-radius: 10px;
    --ram-radius-sm: 6px;
}

[data-theme="dark"] {
    --ram-bg: #1e293b;
    --ram-bg-soft: #0f172a;
    --ram-text: #e2e8f0;
    --ram-text-dim: #94a3b8;
    --ram-border: rgba(255,255,255,0.08);
    --ram-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.2);
    --ram-shadow-lg: 0 4px 6px -1px rgba(0,0,0,0.4), 0 2px 4px -2px rgba(0,0,0,0.3);
}

/* ============ Stats cards (compact, monochrome) ============ */
.ram-stats-row {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
}
.ram-stat-card {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    padding: 0.85rem 1rem;
    box-shadow: var(--ram-shadow);
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    position: relative;
    overflow: hidden;
}
.ram-stat-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--accent, var(--ram-primary));
}
.ram-stat-card.ddr3::before { background: #ef4444; }
.ram-stat-card.ddr4::before { background: #3b82f6; }
.ram-stat-card.ddr5::before { background: #8b5cf6; }
.ram-stat-card .stat-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--ram-text-dim);
}
.ram-stat-card .stat-head .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 6px currentColor;
}
.ram-stat-card.ddr3 .dot { background: #ef4444; color: #ef4444; }
.ram-stat-card.ddr4 .dot { background: #3b82f6; color: #3b82f6; }
.ram-stat-card.ddr5 .dot { background: #8b5cf6; color: #8b5cf6; }
.ram-stat-card .stat-main {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--ram-text);
    line-height: 1.1;
    margin-top: 0.15rem;
}
.ram-stat-card .stat-sub {
    font-size: 0.75rem;
    color: var(--ram-text-dim);
}
.ram-stat-card .stat-bar {
    height: 4px;
    background: rgba(0,0,0,0.06);
    border-radius: 2px;
    margin-top: 0.4rem;
    overflow: hidden;
}
.ram-stat-card .stat-bar > div {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s;
}
.ram-stat-card.ddr3 .stat-bar > div { background: #ef4444; }
.ram-stat-card.ddr4 .stat-bar > div { background: #3b82f6; }
.ram-stat-card.ddr5 .stat-bar > div { background: #8b5cf6; }

/* ============ Capacity mini-grid ============ */
.ram-cap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.ram-cap-card {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius-sm);
    padding: 0.6rem 0.7rem;
    box-shadow: var(--ram-shadow);
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    cursor: pointer;
    transition: all 0.15s;
}
.ram-cap-card:hover {
    transform: translateY(-1px);
    box-shadow: var(--ram-shadow-lg);
    border-color: var(--ram-primary-soft);
}
.ram-cap-card .cap-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--ram-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.ram-cap-card .cap-prices {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.75rem;
}
.ram-cap-card .cap-ddr {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 600;
    color: var(--ram-text);
}
.ram-cap-card .cap-ddr .ddr-dot {
    width: 6px; height: 6px; border-radius: 50%;
    flex-shrink: 0;
}
.ram-cap-card .cap-ddr .ddr-dot.d3 { background: #ef4444; }
.ram-cap-card .cap-ddr .ddr-dot.d4 { background: #3b82f6; }
.ram-cap-card .cap-ddr .ddr-dot.d5 { background: #8b5cf6; }
.ram-cap-card .cap-ddr .count { color: var(--ram-text-dim); font-weight: 400; font-size: 0.7rem; }

/* ============ Filter bar (modern) ============ */
.ram-filterbar {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    padding: 0.75rem 1rem;
    box-shadow: var(--ram-shadow);
    margin-bottom: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
}
.ram-filterbar .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.ram-filterbar .filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--ram-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.ram-filterbar .filter-chips {
    display: flex;
    gap: 0.25rem;
    border: 1px solid var(--ram-border);
    border-radius: 8px;
    padding: 2px;
    background: var(--ram-bg-soft);
}
.ram-filterbar .filter-chips button {
    background: transparent;
    border: none;
    color: var(--ram-text-dim);
    padding: 0.3rem 0.65rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
}
.ram-filterbar .filter-chips button:hover {
    background: var(--ram-bg);
    color: var(--ram-text);
}
.ram-filterbar .filter-chips button.active {
    background: var(--ram-primary);
    color: white;
}
.ram-filterbar select, .ram-filterbar input[type="text"] {
    background: var(--ram-bg-soft);
    border: 1px solid var(--ram-border);
    color: var(--ram-text);
    border-radius: 6px;
    padding: 0.35rem 0.6rem;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
}
.ram-filterbar select:focus, .ram-filterbar input:focus {
    outline: none;
    border-color: var(--ram-primary);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}
.ram-filterbar .check-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.7rem;
    background: var(--ram-bg-soft);
    border: 1px solid var(--ram-border);
    border-radius: 999px;
    font-size: 0.8rem;
    color: var(--ram-text);
    cursor: pointer;
    user-select: none;
    transition: all 0.15s;
}
.ram-filterbar .check-pill:hover { border-color: var(--ram-primary-soft); }
.ram-filterbar .check-pill input { margin: 0; }
.ram-filterbar .check-pill.on { background: var(--ram-primary); color: white; border-color: var(--ram-primary); }
.ram-filterbar .check-pill.on input { filter: invert(1); }
.ram-filterbar .ram-id-input {
    width: 90px;
}
.ram-filterbar .export-btn {
    margin-left: auto;
    background: var(--ram-primary);
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
.ram-filterbar .export-btn:hover {
    background: #4f46e5;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(99, 102, 241, 0.25);
}
.ram-filterbar .divider {
    width: 1px;
    height: 22px;
    background: var(--ram-border);
    margin: 0 0.25rem;
}

/* ============ Deal strip (top deals) ============ */
.ram-deals-strip {
    background: linear-gradient(135deg, rgba(239,68,68,0.05) 0%, rgba(245,158,11,0.05) 100%);
    border: 1px solid rgba(239,68,68,0.15);
    border-radius: var(--ram-radius);
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
}
.ram-deals-strip h3 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    color: var(--ram-text);
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.ram-deals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.5rem;
}
.ram-deal-card {
    display: flex;
    gap: 0.65rem;
    align-items: center;
    padding: 0.6rem;
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius-sm);
    cursor: pointer;
    transition: all 0.15s;
}
.ram-deal-card:hover {
    border-color: var(--ram-error);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(239,68,68,0.15);
}
.ram-deal-card .deal-img {
    width: 44px; height: 44px;
    border-radius: 6px;
    object-fit: cover;
    border: 1px solid var(--ram-border);
    flex-shrink: 0;
    background: var(--ram-bg-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ram-text-dim);
    font-size: 1.1rem;
}
.ram-deal-card .deal-info {
    flex: 1;
    min-width: 0;
}
.ram-deal-card .deal-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--ram-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.ram-deal-card .deal-meta {
    font-size: 0.7rem;
    color: var(--ram-text-dim);
    margin-top: 0.1rem;
}
.ram-deal-card .deal-price {
    text-align: right;
    flex-shrink: 0;
}
.ram-deal-card .deal-price-main {
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--ram-error);
    line-height: 1.1;
}
.ram-deal-card .deal-save {
    font-size: 0.7rem;
    color: var(--ram-success);
    font-weight: 700;
}
.ram-deal-card .deal-avg {
    font-size: 0.65rem;
    color: var(--ram-text-dim);
    text-decoration: line-through;
}

/* ============ Listings table (modernized) ============ */
.ram-listings {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    overflow: hidden;
    box-shadow: var(--ram-shadow);
}
.ram-listings table {
    width: 100%;
    border-collapse: collapse;
    table-layout: auto;
}
.ram-listings thead {
    background: var(--ram-bg-soft);
    border-bottom: 1px solid var(--ram-border);
}
.ram-listings thead th {
    text-align: left;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--ram-text-dim);
    padding: 0.65rem 0.85rem;
    white-space: nowrap;
}
.ram-listings tbody tr {
    border-bottom: 1px solid var(--ram-border);
    transition: background 0.1s;
}
.ram-listings tbody tr:last-child { border-bottom: none; }
.ram-listings tbody tr.clickable { cursor: pointer; }
.ram-listings tbody tr:hover {
    background: rgba(99, 102, 241, 0.04);
}
.ram-listings tbody td {
    padding: 0.7rem 0.85rem;
    font-size: 0.85rem;
    color: var(--ram-text);
    vertical-align: middle;
}

/* Image cell */
.ram-cell-image {
    position: relative;
    width: 72px;
    padding: 0.4rem 0.6rem !important;
}
.ram-cell-image img {
    width: 60px;
    height: 60px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid var(--ram-border);
    background: var(--ram-bg-soft);
    cursor: zoom-in;
}
.ram-cell-image .deal-badge-stack {
    position: absolute;
    top: 2px;
    left: 2px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 2;
}
.ram-cell-image .deal-badge-stack .badge {
    font-size: 0.6rem;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    line-height: 1.4;
}
.ram-cell-image .deal-badge-stack .badge.steal {
    background: var(--ram-error);
    color: white;
    box-shadow: 0 0 6px rgba(239,68,68,0.5);
}
.ram-cell-image .deal-badge-stack .badge.is-new {
    background: var(--ram-success);
    color: white;
}
.ram-cell-image .deal-badge-stack .badge.unicorn {
    background: linear-gradient(135deg, #a855f7, #ec4899);
    color: white;
}
.ram-cell-image .placeholder-img {
    width: 60px;
    height: 60px;
    border-radius: 6px;
    background: var(--ram-bg-soft);
    border: 1px solid var(--ram-border);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ram-text-dim);
    font-size: 1.2rem;
}

/* RAM name cell */
.ram-cell-name .ram-title {
    font-weight: 600;
    color: var(--ram-text);
    font-size: 0.9rem;
    line-height: 1.3;
    margin-bottom: 0.25rem;
}
.ram-cell-name .ram-attrs {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
    margin-bottom: 0.3rem;
}
.ram-cell-name .ddr-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    color: white;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.ram-cell-name .ddr-chip.d3 { background: #ef4444; }
.ram-cell-name .ddr-chip.d4 { background: #3b82f6; }
.ram-cell-name .ddr-chip.d5 { background: #8b5cf6; }
.ram-cell-name .cap-chip {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--ram-text);
    background: var(--ram-bg-soft);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid var(--ram-border);
}
.ram-cell-name .speed-text {
    font-size: 0.7rem;
    color: var(--ram-text-dim);
}
.ram-cell-name .conf-bar {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
}
.ram-cell-name .conf-bar-track {
    flex: 1;
    height: 3px;
    background: rgba(0,0,0,0.06);
    border-radius: 2px;
    overflow: hidden;
    max-width: 60px;
}
.ram-cell-name .conf-bar-fill {
    height: 100%;
    border-radius: 2px;
}
.ram-cell-name .conf-bar-fill.high { background: var(--ram-success); }
.ram-cell-name .conf-bar-fill.medium { background: var(--ram-warning); }
.ram-cell-name .conf-bar-fill.low { background: var(--ram-error); }
.ram-cell-name .conf-label { color: var(--ram-text-dim); font-weight: 600; }

/* Price cell */
.ram-cell-price .price-main {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--ram-text);
    line-height: 1.2;
}
.ram-cell-price .price-main.below { color: var(--ram-success); }
.ram-cell-price .price-main.above { color: var(--ram-error); }
.ram-cell-price .price-meta {
    font-size: 0.72rem;
    color: var(--ram-text-dim);
    margin-top: 0.15rem;
}
.ram-cell-price .price-pg {
    font-weight: 600;
    color: var(--ram-text);
}
.ram-cell-price .price-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 4px;
    margin-top: 0.3rem;
    text-transform: uppercase;
}
.ram-cell-price .price-tag.below { background: rgba(16,185,129,0.1); color: var(--ram-success); }
.ram-cell-price .price-tag.above { background: rgba(239,68,68,0.1); color: var(--ram-error); }

/* Latency cell */
.ram-cell-latency {
    font-weight: 600;
    color: var(--ram-text);
    font-family: 'SF Mono', Menlo, Consolas, monospace;
    font-size: 0.85rem;
}
.ram-cell-latency.empty { color: var(--ram-text-dim); font-weight: 400; }

/* Stat block cell (Model/Market Position) */
.ram-cell-stat {
    min-width: 130px;
}
.ram-cell-stat .stat-head {
    font-size: 0.7rem;
    color: var(--ram-text-dim);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 0.2rem;
}
.ram-cell-stat .stat-value {
    font-size: 0.85rem;
    color: var(--ram-text);
    font-weight: 700;
    margin-bottom: 0.1rem;
}
.ram-cell-stat .stat-range {
    font-size: 0.7rem;
    color: var(--ram-text-dim);
    margin-bottom: 0.3rem;
}
.ram-cell-stat .stat-bar {
    height: 4px;
    background: rgba(0,0,0,0.06);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 0.2rem;
}
.ram-cell-stat .stat-bar > div {
    height: 100%;
    background: var(--ram-primary);
    border-radius: 2px;
}
.ram-cell-stat .stat-pct {
    font-size: 0.7rem;
    color: var(--ram-text-dim);
    font-weight: 600;
}
.ram-cell-stat .stat-pct .pct-num { color: var(--ram-text); }

/* Location + Date */
.ram-cell-meta {
    font-size: 0.8rem;
    color: var(--ram-text);
    line-height: 1.4;
}
.ram-cell-meta .meta-line {
    color: var(--ram-text-dim);
    font-size: 0.7rem;
}

/* Action cell */
.ram-cell-actions {
    white-space: nowrap;
    text-align: right;
}
.ram-action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: 1px solid var(--ram-border);
    background: var(--ram-bg-soft);
    color: var(--ram-text-dim);
    border-radius: 6px;
    cursor: pointer;
    margin-left: 0.2rem;
    transition: all 0.15s;
    font-size: 0.85rem;
}
.ram-action-btn:hover {
    background: var(--ram-primary);
    color: white;
    border-color: var(--ram-primary);
}
.ram-action-btn.flag:hover {
    background: var(--ram-error);
    border-color: var(--ram-error);
}

/* ============ Charts (slim) ============ */
.ram-charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
}
.ram-chart-card {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    padding: 0.85rem 1rem;
    box-shadow: var(--ram-shadow);
}
.ram-chart-card h3 {
    margin: 0 0 0.5rem 0;
    font-size: 0.85rem;
    color: var(--ram-text);
}
.ram-chart-card .chart-container {
    height: 200px;
    position: relative;
}
.ram-chart-card.full {
    grid-column: 1 / -1;
}

/* ============ Trends section ============ */
.ram-trends {
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    padding: 0.85rem 1rem;
    box-shadow: var(--ram-shadow);
    margin-top: 1rem;
}
.ram-trends h3 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    color: var(--ram-text);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    flex-wrap: wrap;
}
.ram-trends .period-btns {
    display: inline-flex;
    gap: 0.25rem;
    border: 1px solid var(--ram-border);
    border-radius: 6px;
    padding: 2px;
    background: var(--ram-bg-soft);
}
.ram-trends .period-btns button {
    background: transparent;
    border: none;
    color: var(--ram-text-dim);
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
}
.ram-trends .period-btns button.active {
    background: var(--ram-primary);
    color: white;
}

/* ============ Misc ============ */
.ram-loading, .ram-empty {
    text-align: center;
    padding: 2.5rem 1rem;
    color: var(--ram-text-dim);
    font-size: 0.9rem;
}
.ram-empty { font-style: italic; }

.ram-summary-row {
    background: var(--ram-bg-soft);
    border-top: 2px solid var(--ram-border);
    font-weight: 700;
}
.ram-summary-row td {
    padding: 0.65rem 0.85rem !important;
    font-size: 0.85rem;
}
.ram-summary-row .summary-label {
    text-align: right;
    color: var(--ram-text-dim);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.5px;
}
.ram-summary-row .summary-amount {
    color: var(--ram-text);
    font-weight: 800;
    font-size: 1rem;
}
.ram-summary-row .summary-count {
    color: var(--ram-text-dim);
    font-size: 0.75rem;
}

/* Popup */
#model-history-popup {
    position: absolute;
    background: var(--ram-bg);
    border: 1px solid var(--ram-border);
    border-radius: var(--ram-radius);
    padding: 0.85rem 1rem;
    z-index: 1000;
    box-shadow: var(--ram-shadow-lg);
    min-width: 280px;
    max-width: 360px;
    font-size: 0.85rem;
}
#model-history-popup h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.85rem;
    color: var(--ram-text);
}
#model-history-popup .seen-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
#model-history-popup .seen-badge.seen { background: var(--ram-success); color: white; }
#model-history-popup .seen-badge.new { background: var(--ram-warning); color: white; }
#model-history-popup .price-row {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0;
    border-bottom: 1px dashed var(--ram-border);
}
#model-history-popup .price-row:last-child { border: none; }
#model-history-popup .price-row .label { color: var(--ram-text-dim); font-size: 0.8rem; }
#model-history-popup .price-row .value { font-weight: 700; }
#model-history-popup .price-row .value.better { color: var(--ram-success); }
#model-history-popup .price-row .value.worse { color: var(--ram-error); }

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.ram-loading::after {
    content: '';
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid var(--ram-primary);
    border-top-color: transparent;
    border-radius: 50%;
    margin-left: 0.5rem;
    animation: spin 1s linear infinite;
    vertical-align: middle;
}

/* Responsive */
@media (max-width: 900px) {
    .ram-stats-row { grid-template-columns: 1fr 1fr; }
    .ram-charts-row { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
    .ram-stats-row { grid-template-columns: 1fr; }
    .ram-filterbar { flex-direction: column; align-items: stretch; }
    .ram-filterbar .export-btn { margin-left: 0; width: 100%; justify-content: center; }
    .ram-deals-grid { grid-template-columns: 1fr; }
}
</style>
{% endblock %}'''

# Find and replace the CSS block
import re
new_text = re.sub(
    r'\{% block extra_css %\}.*?\{% endblock %\}',
    new_css,
    text,
    count=1,
    flags=re.DOTALL,
)
print(f"CSS replaced. Was {len(text)} chars, now {len(new_text)} chars")
FILE.write_text(new_text, encoding="utf-8")
print("Done")
