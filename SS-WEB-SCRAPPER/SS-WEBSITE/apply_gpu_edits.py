import re

path = 'templates/gpu.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. T260 - Enhance compare-row-checked styling
old_compare_css = """    tr.compare-row-checked td {
        background: rgba(102, 126, 234, 0.12) !important;
        box-shadow: inset 0 0 12px rgba(102, 126, 234, 0.18);
    }"""
new_compare_css = """    tr.compare-row-checked td {
        background: rgba(102, 126, 234, 0.15) !important;
        box-shadow: inset 0 0 14px rgba(102, 126, 234, 0.22);
        border-left: 3px solid #667eea;
    }
    tr.compare-row-checked:hover td {
        background: rgba(102, 126, 234, 0.22) !important;
    }"""
assert old_compare_css in text, 'compare css not found'
text = text.replace(old_compare_css, new_compare_css)

# 2. T244 - Center Image header/cell
old_header = """                    <tr>
                        <th>Image</th>
                        <th>Brand</th>"""
new_header = """                    <tr>
                        <th class="text-center">Image</th>
                        <th>Brand</th>"""
assert old_header in text, 'image header not found'
text = text.replace(old_header, new_header)

old_image_cell = """                    <td class="listing-image-cell" style="position: relative; text-align: center;">
                        <div style="position: relative; display: inline-block;">"""
new_image_cell = """                    <td class="listing-image-cell text-center" style="position: relative;">
                        <div style="position: relative; display: inline-block;">"""
assert old_image_cell in text, 'image cell not found'
text = text.replace(old_image_cell, new_image_cell)

# 3. T256/T263 - Source badge under vendor badge + keep dot in image column
old_source_block = """            // Source dot indicator (small colored dot only) - check if enabled in settings
            const showSourceDots = localStorage.getItem('showSourceDots') !== 'false';
            let sourceDot = '';
            const sourceLabels = {
                'andelemandele': { text: 'Andele', bg: '#8B5CF6' },
                'facebook_extension': { text: 'FB', bg: '#1877F2' },
                'ss.com': { text: 'SS', bg: '#10b981' }
            };
            const sourceInfo = sourceLabels[item.source] || sourceLabels['ss.com'];
            if (showSourceDots) {
                sourceDot = `<span class="source-dot" title="${sourceInfo.text}" style="display: inline-block; width: 10px; height: 10px; background: ${sourceInfo.bg}; border-radius: 50%; cursor: pointer; box-shadow: 0 0 4px ${sourceInfo.bg}; flex-shrink: 0;"></span>`;
            }"""
new_source_block = """            // Source dot indicator (small colored dot only, no text) - check if enabled in settings
            const showSourceDots = localStorage.getItem('showSourceDots') !== 'false';
            let sourceDot = '';
            let sourceBadge = '';
            const sourceLabels = {
                'andelemandele': { text: 'Andele', bg: '#8B5CF6' },
                'facebook_extension': { text: 'FB', bg: '#1877F2' },
                'ss.com': { text: 'SS', bg: '#10b981' }
            };
            const sourceInfo = sourceLabels[item.source] || sourceLabels['ss.com'];
            if (showSourceDots) {
                sourceDot = `<span class="source-dot" title="${sourceInfo.text}" style="display: inline-block; width: 10px; height: 10px; background: ${sourceInfo.bg}; border-radius: 50%; cursor: pointer; box-shadow: 0 0 4px ${sourceInfo.bg}; flex-shrink: 0;"></span>`;
                sourceBadge = `<span class="source-badge" title="${sourceInfo.text}" style="display: inline-block; background: ${sourceInfo.bg}; color: white; font-size: 0.6rem; font-weight: bold; padding: 2px 5px; border-radius: 4px; margin-top: 4px; line-height: 1;">${sourceInfo.text}</span>`;
            }"""
assert old_source_block in text, 'source block not found'
text = text.replace(old_source_block, new_source_block)

old_brand_cell = """                    <td class="text-center">
                        ${vendorBadge}
                    </td>"""
new_brand_cell = """                    <td class="text-center" style="display: table-cell; vertical-align: middle;">
                        ${vendorBadge}
                        ${sourceBadge}
                    </td>"""
assert old_brand_cell in text, 'brand cell not found'
text = text.replace(old_brand_cell, new_brand_cell)

# 4. T262 - Price drop badge smaller and over the price
old_price_drop = """                            ${priceDecreasedBadge ? `<span style="position: absolute; top: -10px; left: 0; transform: translateY(-100%); font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; background: #16a34a; color: white; font-weight: bold; white-space: nowrap; z-index: 5;">↓ Drop</span>` : ''}"""
new_price_drop = """                            ${priceDecreasedBadge ? `<span style="position: absolute; top: -4px; right: -4px; transform: translate(20%, -80%); font-size: 0.55rem; padding: 1px 4px; border-radius: 3px; background: #16a34a; color: white; font-weight: bold; white-space: nowrap; z-index: 5; box-shadow: 0 1px 3px rgba(0,0,0,0.3);">↓ Drop</span>` : ''}"""
assert old_price_drop in text, 'price drop badge not found'
text = text.replace(old_price_drop, new_price_drop)

# 5. T242 - Remove Top Performers from loadPerformanceCharts (it will be driven by filtered listings)
old_topperf_in_perf = """        // 4. Top Performers chart - true G3D Mark per Euro (higher = better value)
        const ctxTop = document.getElementById('gpu-top-performers-chart');
        if (ctxTop && data.scatter && data.scatter.length) {
            const topPerformers = data.scatter
                .filter(p => Number(p.g3d_mark) > 0 && Number(p.avg_price) > 0)
                .map(p => ({ ...p, true_ratio: Number(p.g3d_mark) / Number(p.avg_price) }))
                .sort((a, b) => b.true_ratio - a.true_ratio)
                .slice(0, 10);
            new Chart(ctxTop, {
                type: 'bar',
                data: {
                    labels: topPerformers.map(p => `${p.vendor} ${p.model.replace(/\\b(GeForce|Radeon)\\s*/i, '').trim()}`),
                    datasets: [{
                        label: 'G3D/€',
                        data: topPerformers.map(p => p.true_ratio),
                        backgroundColor: topPerformers.map((_, i) => i < 3 ? 'rgba(16, 185, 129, 0.85)' : 'rgba(59, 130, 246, 0.6)'),
                        borderColor: topPerformers.map((_, i) => i < 3 ? 'rgba(16, 185, 129, 1)' : 'rgba(59, 130, 246, 0.8)'),
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: { title: { display: true, text: 'G3D Mark per Euro (higher is better)' } }
                    },
                    plugins: {
                        title: { display: true, text: '🏆 Top Performers (G3D/€)' },
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const p = topPerformers[ctx.dataIndex];
                                    const vramGb = p.vram_gb >= 1024 ? `${Math.round(p.vram_gb/1024)}GB` : `${p.vram_gb}GB`;
                                    return `${p.model}${p.vram_gb ? ' · ' + vramGb : ''}: ${p.true_ratio.toFixed(2)} G3D/€ · avg €${Number(p.avg_price).toFixed(0)} · ${p.listing_count} listings`;
                                }
                            }
                        }
                    }
                }
            });
        }"""
new_topperf_in_perf = """        // 4. Top Performers chart is now driven by filtered listings in loadListings()"""
assert old_topperf_in_perf in text, 'top performers in loadPerformanceCharts not found'
text = text.replace(old_topperf_in_perf, new_topperf_in_perf)

# 6. T258 - Rewrite updateMonthlyAvgChart to show individual listings as points
old_monthly_func = """function updateMonthlyAvgChart(listings) {
    const ctx = document.getElementById('gpu-monthly-avg-chart');
    if (!ctx) return;

    // Group by model + month so each model has its own line
    const modelMonthMap = {};
    listings.forEach(item => {
        const date = item.date_posted || item.first_seen_at;
        if (!date) return;
        const month = new Date(date).toISOString().slice(0, 7);
        const model = item.gpu_model || item.title || 'Unknown';
        const key = `${model}__${month}`;
        if (!modelMonthMap[key]) {
            modelMonthMap[key] = { model, month, total: 0, count: 0 };
        }
        modelMonthMap[key].total += parseFloat(item.price_eur) || 0;
        modelMonthMap[key].count += 1;
    });

    // All months across the filtered listings
    const months = Array.from(new Set(Object.values(modelMonthMap).map(d => d.month))).sort();
    const labels = months.map(m => {
        const [y, mon] = m.split('-');
        return `${mon}/${y}`;
    });

    // Build a dataset per model
    const byModel = {};
    Object.values(modelMonthMap).forEach(d => {
        if (!byModel[d.model]) byModel[d.model] = {};
        byModel[d.model][d.month] = d.total / d.count;
    });

    const palette = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8B5CF6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'];
    const datasets = Object.entries(byModel).map(([model, monthData], idx) => ({
        label: model.replace(/\\b(GeForce|Radeon|AMD|NVIDIA|Intel)\\s*/gi, '').trim(),
        data: months.map(m => monthData[m] || null),
        borderColor: palette[idx % palette.length],
        backgroundColor: palette[idx % palette.length],
        fill: false,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
        spanGaps: true
    }));

    if (monthlyAvgChart) monthlyAvgChart.destroy();
    monthlyAvgChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: true, position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const val = Number(ctx.raw);
                            if (!Number.isFinite(val)) return null;
                            return `${ctx.dataset.label}: €${val.toFixed(0)}`;
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: false, title: { display: true, text: 'Price (€)' } },
                x: { title: { display: true, text: 'Month' } }
            }
        }
    });
}"""
new_monthly_func = """function updateMonthlyAvgChart(listings) {
    const ctx = document.getElementById('gpu-monthly-avg-chart');
    if (!ctx) return;

    // Collect months
    const months = Array.from(new Set(
        listings.map(item => {
            const d = item.date_posted || item.first_seen_at;
            return d ? new Date(d).toISOString().slice(0, 7) : null;
        }).filter(Boolean)
    )).sort();
    const labels = months.map(m => { const [y, mon] = m.split('-'); return `${mon}/${y}`; });
    const monthIndex = Object.fromEntries(months.map((m, i) => [m, i]));

    // Group individual listings by model; each point is one card/listing
    const byModel = {};
    listings.forEach(item => {
        const d = item.date_posted || item.first_seen_at;
        if (!d) return;
        const month = new Date(d).toISOString().slice(0, 7);
        const model = item.gpu_model || item.title || 'Unknown';
        if (!byModel[model]) byModel[model] = [];
        byModel[model].push({
            x: monthIndex[month],
            y: parseFloat(item.price_eur) || 0,
            label: item.gpu_model || item.title
        });
    });

    const palette = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8B5CF6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'];
    const datasets = Object.entries(byModel).map(([model, points], idx) => ({
        label: model.replace(/\\b(GeForce|Radeon|AMD|NVIDIA|Intel)\\s*/gi, '').trim(),
        data: points,
        borderColor: palette[idx % palette.length],
        backgroundColor: palette[idx % palette.length],
        showLine: false,
        pointRadius: 5,
        pointHoverRadius: 7
    }));

    if (monthlyAvgChart) monthlyAvgChart.destroy();
    monthlyAvgChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            parsing: { x: 'x', y: 'y' },
            plugins: {
                legend: { display: true, position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: €${Number(ctx.raw.y).toFixed(0)}`
                    }
                }
            },
            scales: {
                y: { beginAtZero: false, title: { display: true, text: 'Price (€)' } },
                x: {
                    type: 'linear',
                    position: 'bottom',
                    min: -0.5,
                    max: months.length - 0.5,
                    title: { display: true, text: 'Month' },
                    ticks: {
                        stepSize: 1,
                        callback: v => labels[Math.round(v)] || ''
                    }
                }
            }
        }
    });
}"""
assert old_monthly_func in text, 'monthly avg function not found'
text = text.replace(old_monthly_func, new_monthly_func)

# 7. T259 - Extract source distribution builder and update with filtered listings
# Insert helper before updateMonthlyAvgChart
helper_source = """function buildSourceDistributionHtml(listings) {
    const sourceStats = {};
    listings.forEach(item => {
        const source = item.source || 'Unknown';
        sourceStats[source] = (sourceStats[source] || 0) + 1;
    });

    const sourceNames = {
        'ss.com': 'SS.com',
        'andelemandele': 'Andele',
        'facebook_extension': 'Facebook',
        'facebook': 'Facebook'
    };

    const sourceDisplayCounts = {};
    Object.entries(sourceStats).forEach(([source, count]) => {
        const key = sourceNames[source] || source;
        sourceDisplayCounts[key] = (sourceDisplayCounts[key] || 0) + count;
    });

    const sourceEntries = Object.entries(sourceDisplayCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
    const totalSource = sourceEntries.reduce((sum, [, count]) => sum + count, 0) || 1;

    const sourceColors = {
        'SS.com': '#90EE90',
        'Andele': '#8B5CF6',
        'Facebook': '#1877F2'
    };
    const sourceIcons = {
        'SS.com': '📰',
        'Andele': '📱',
        'Facebook': '👥'
    };

    let sourceHtml = '<div style="display: flex; flex-direction: column; gap: 0.4rem;">';
    sourceEntries.forEach(([source, count]) => {
        const pct = (count / totalSource * 100).toFixed(0);
        const icon = sourceIcons[source] || '📦';
        const barWidth = sourceEntries[0] ? (count / sourceEntries[0][1] * 100) : 0;
        const color = sourceColors[source] || '#888';
        sourceHtml += `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.1rem;">${icon}</span>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 2px;">
                        <span>${source}</span>
                        <span style="font-weight: bold;">${pct}%</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; overflow: hidden;">
                        <div style="background: ${color}; height: 100%; width: ${barWidth}%; border-radius: 4px;"></div>
                    </div>
                </div>
                <span style="font-size: 0.75rem; color: #888; min-width: 35px; text-align: right;">${count}</span>
            </div>
        `;
    });
    sourceHtml += '</div>';
    return sourceHtml;
}

let monthlyAvgChart = null;"""
old_monthly_var = "let monthlyAvgChart = null;"
assert old_monthly_var in text, 'monthlyAvgChart var not found'
text = text.replace(old_monthly_var, helper_source)

# Replace inline source distribution block inside loadGPUStatistics with helper call
old_source_inline = """        // 3. Source Distribution
        const sourceStats = {};
        listings.forEach(item => {
            const source = item.source || 'Unknown';
            sourceStats[source] = (sourceStats[source] || 0) + 1;
        });

        const sourceNames = {
            'ss.com': 'SS.com',
            'andelemandele': 'Andele',
            'facebook_extension': 'Facebook',
            'facebook': 'Facebook'
        };

        const sourceDisplayCounts = {};
        Object.entries(sourceStats).forEach(([source, count]) => {
            const key = sourceNames[source] || source;
            sourceDisplayCounts[key] = (sourceDisplayCounts[key] || 0) + count;
        });

        const sourceEntries = Object.entries(sourceDisplayCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        const totalSource = sourceEntries.reduce((sum, [, count]) => sum + count, 0) || 1;

        // Bright colors for source chart
        const sourceColors = {
            'SS.com': '#90EE90',
            'Andele': '#8B5CF6',
            'Facebook': '#1877F2'
        };
        const sourceIcons = {
            'SS.com': '📰',
            'Andele': '📱',
            'Facebook': '👥'
        };

        let sourceHtml = '<div style="display: flex; flex-direction: column; gap: 0.4rem;">';
        sourceEntries.forEach(([source, count], idx) => {
            const pct = (count / totalSource * 100).toFixed(0);
            const icon = sourceIcons[source] || '📦';
            const barWidth = (count / sourceEntries[0][1] * 100);
            const color = sourceColors[source] || '#888';
            sourceHtml += `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.1rem;">${icon}</span>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 2px;">
                            <span>${source}</span>
                            <span style="font-weight: bold;">${pct}%</span>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; overflow: hidden;">
                            <div style="background: ${color}; height: 100%; width: ${barWidth}%; border-radius: 4px;"></div>
                        </div>
                    </div>
                    <span style="font-size: 0.75rem; color: #888; min-width: 35px; text-align: right;">${count}</span>
                </div>
            `;
        });
        sourceHtml += '</div>';
        document.getElementById('source-distribution').innerHTML = sourceHtml;"""
new_source_inline = """        // 3. Source Distribution
        document.getElementById('source-distribution').innerHTML = buildSourceDistributionHtml(listings);"""
assert old_source_inline in text, 'inline source distribution not found'
text = text.replace(old_source_inline, new_source_inline)

# 8. Add updateTopPerformersChart and call in loadListings
old_top_var = """let priceChart = null;
let historyChart = null;
let mostSoldChart = null;"""
new_top_var = """let priceChart = null;
let historyChart = null;
let mostSoldChart = null;
let topPerformersChart = null;"""
assert old_top_var in text, 'chart vars not found'
text = text.replace(old_top_var, new_top_var)

# Add updateTopPerformersChart after updateMonthlyAvgChart function
# We will insert right after the closing of new_monthly_func. It ends with:
# "    });
# }\n\nfunction updateSummaryRowColspans()"
insert_after = """    });
}

function updateSummaryRowColspans()"""
assert insert_after in text, 'insert point after monthlyAvg not found'
top_performers_func = """
function updateTopPerformersChart(listings) {
    const ctx = document.getElementById('gpu-top-performers-chart');
    if (!ctx) return;

    const top = listings
        .filter(l => Number(l.g3d_mark) > 0 && Number(l.price_eur) > 0)
        .map(l => ({ ...l, ratio: Number(l.g3d_mark) / Number(l.price_eur) }))
        .sort((a, b) => b.ratio - a.ratio)
        .slice(0, 10);

    if (topPerformersChart) topPerformersChart.destroy();
    topPerformersChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(l => {
                const model = (l.gpu_model || l.title || '').replace(/\\b(GeForce|Radeon|AMD|NVIDIA|Intel)\\s*/gi, '').trim();
                return `${l.vendor || ''} ${model}`.trim();
            }),
            datasets: [{
                label: 'G3D/€',
                data: top.map(l => l.ratio),
                backgroundColor: top.map((_, i) => i < 3 ? 'rgba(16, 185, 129, 0.85)' : 'rgba(59, 130, 246, 0.6)'),
                borderColor: top.map((_, i) => i < 3 ? 'rgba(16, 185, 129, 1)' : 'rgba(59, 130, 246, 0.8)'),
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { title: { display: true, text: 'G3D Mark per Euro (higher is better)' } }
            },
            plugins: {
                title: { display: true, text: '🏆 Top Performers (G3D/€)' },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const l = top[ctx.dataIndex];
                            return `€${Number(l.price_eur).toFixed(0)} · ${l.ratio.toFixed(2)} G3D/€ · G3D ${Number(l.g3d_mark).toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}
"""
text = text.replace(insert_after, "    });\n}" + top_performers_func + "\nfunction updateSummaryRowColspans")

# Call updateTopPerformersChart and update source distribution in loadListings
old_chart_calls = """        // Update chart
        updatePriceChart(listings);
        updateMonthlyAvgChart(listings);"""
new_chart_calls = """        // Update charts
        updatePriceChart(listings);
        updateMonthlyAvgChart(listings);
        updateTopPerformersChart(listings);
        document.getElementById('source-distribution').innerHTML = buildSourceDistributionHtml(listings);"""
assert old_chart_calls in text, 'chart calls in loadListings not found'
text = text.replace(old_chart_calls, new_chart_calls)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print('gpu.html edits applied')

# gpu_compare.html - make selected listing price more explicit
path2 = 'templates/gpu_compare.html'
with open(path2, 'r', encoding='utf-8') as f:
    text2 = f.read()
old_header_price = """        selected.forEach(l => {
            html += `<th style="text-align:center; min-width:180px;"><div style="font-weight:600;">${l.gpu_model || l.title}</div><div style="font-size:0.95rem;color:var(--accent-color, #3b82f6);font-weight:700;margin-top:0.25rem;">${fmtPrice(l.price_eur)}</div></th>`;
        });"""
new_header_price = """        selected.forEach(l => {
            html += `<th style="text-align:center; min-width:180px;"><div style="font-weight:600;">${l.gpu_model || l.title}</div><div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.25rem;">Selected listing price</div><div style="font-size:0.95rem;color:var(--accent-color, #3b82f6);font-weight:700;">${fmtPrice(l.price_eur)}</div></th>`;
        });"""
if old_header_price in text2:
    text2 = text2.replace(old_header_price, new_header_price)
    with open(path2, 'w', encoding='utf-8') as f:
        f.write(text2)
    print('gpu_compare.html edits applied')
else:
    print('gpu_compare.html header price block not found, skipping')
