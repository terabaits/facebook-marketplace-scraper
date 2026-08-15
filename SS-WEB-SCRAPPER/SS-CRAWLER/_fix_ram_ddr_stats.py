"""Fix updateDDRStats and updateCapacityCards to use the new HTML element IDs."""
from pathlib import Path

FILE = Path(r"G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE\templates\ram.html")
text = FILE.read_text(encoding="utf-8")

# The actual current content in the file (use the exact bytes from the file)
import re

# Find the existing block
start_marker = "// Update DDR type stats cards\nfunction updateDDRStats(listings) {"
end_marker = "// Update capacity distribution chart"

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)
print(f"start_idx={start_idx}, end_idx={end_idx}")
print(f"len of block to replace: {end_idx - start_idx}")

if start_idx < 0 or end_idx < 0:
    raise SystemExit("Could not find the DDR stats block")

# New block: uses the new HTML IDs (stat-ddr3-active, stat-ddr3-avg, stat-ddr3-median, stat-ddr3-bar, cap-N-dN)
new_block = '''// Update DDR-specific top stats (active count, avg, median, bar)
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
        if (avgEl) avgEl.textContent = d.prices.length ? '\u20ac' + (d.prices.reduce((a,b)=>a+b,0)/d.prices.length).toFixed(0) + ' avg' : '\u20ac\u2014 avg';
        if (medEl) {
            const sorted = [...d.prices].sort((a,b)=>a-b);
            const med = sorted.length ? sorted[Math.floor(sorted.length/2)] : 0;
            medEl.textContent = sorted.length ? '\u20ac' + med.toFixed(0) + ' median' : '\u20ac\u2014 median';
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
            if (el) el.textContent = buckets[cap] && buckets[cap][type] ? buckets[cap][type] : '\u2014';
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
}

'''

# Replace the block (everything from "// Update DDR type stats cards" to (but not including) "// Update capacity distribution chart")
new_text = text[:start_idx] + new_block + text[end_idx:]
FILE.write_text(new_text, encoding="utf-8")
print(f"Done. Old len={len(text)}, new len={len(new_text)}")
print(f"New file written: {FILE}")
