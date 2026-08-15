
let priceHistoryChart = null;
let currentListingId = null;
let currentListingTitle = '';
let selectedComponents = new Set();

// Admin mode check
function isAdminMode() {
    return localStorage.getItem('adminPrebuiltToggle') === 'true';
}

// Unmark a listing as prebuilt (admin only)
async function unmarkPrebuilt(listingId) {
    if (!isAdminMode()) {
        alert('Admin mode required');
        return;
    }
    
    if (!confirm('Remove prebuilt flag from this listing?')) return;
    
    try {
        const response = await fetch('/api/unmark-prebuilt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ listing_id: listingId })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Prebuilt flag removed');
            loadComputers();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error unmarking:', error);
        alert('Failed to unmark');
    }
}

async function loadStats() {
    try {
        console.log('Loading computer stats...');
        const response = await fetch('/api/computers/stats');
        const data = await response.json();
        console.log('Stats response:', data);
        
        if (data.success) {
            document.getElementById('stat-total').textContent = data.stats.total;
            document.getElementById('stat-active').textContent = data.stats.active;
            document.getElementById('stat-avg-price').textContent = '€' + (data.stats.avg_price || 0).toFixed(0);
            document.getElementById('stat-with-cpu-gpu').textContent = (data.stats.with_cpu || 0) + ' / ' + (data.stats.with_gpu || 0);
        } else {
            console.error('Stats error:', data.error);
            document.getElementById('stat-total').textContent = 'Error';
            document.getElementById('stat-active').textContent = 'Error';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stat-total').textContent = 'Error';
        document.getElementById('stat-active').textContent = 'Error';
    }
}

// Strip the SS.COM category breadcrumb from a raw listing title
function cleanComputerTitle(title) {
    if (!title) return '';
    let t = String(title)
        .replace(/^Datori un orgtehnika\s*[\\/\-]?\s*Datori[,\s]+Cena\s*\d+\s*[\u20ac\u20bd\$]\.?\s*/i, '')
        .replace(/^Datori un orgtehnika\s*[\\/\-]?\s*Dat[ao]ri\s*[\\/\-]?\s*P[\u0101a]rdod\s*/i, '')
        .replace(/^Datori un orgtehnika\s*[\\/\-]?\s*/i, '')
        .replace(/\s*-\s*Sludin\u0101jumi\s*$/i, '')
        .replace(/\s*-\s*Sludinajumi\s*$/i, '')
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

async function loadComputers() {
    const activeOnly = document.getElementById('toggle-active') ? document.getElementById('toggle-active').classList.contains('on') : true;
    const prebuiltOnly = document.getElementById('toggle-prebuilt') ? document.getElementById('toggle-prebuilt').classList.contains('on') : false;
    const hidePrebuilt = document.getElementById('toggle-hide-prebuilt') ? document.getElementById('toggle-hide-prebuilt').classList.contains('on') : false;
    const sortBy = document.getElementById('sort-by').value;
    const sortOrder = document.getElementById('sort-order').value;
    
    // Save toggle states to localStorage
    localStorage.setItem('computersPrebuiltOnly', prebuiltOnly);
    localStorage.setItem('computersHidePrebuilt', hidePrebuilt);
    localStorage.setItem('computersSortBy', sortBy);
    localStorage.setItem('computersSortOrder', sortOrder);
    
    const params = new URLSearchParams();
    params.append('active', activeOnly);
    if (prebuiltOnly) params.append('prebuilt', 'only');
    if (hidePrebuilt) params.append('prebuilt', 'exclude');
    params.append('sort', sortBy);
    params.append('order', sortOrder);
    
    try {
        const response = await fetch('/api/computers?' + params.toString());
        const data = await response.json();
        
        const container = document.getElementById('listings-container');
        
        if (!data.success || data.listings.length === 0) {
            container.innerHTML = '<div class="loading">No computer listings found</div>';
            return;
        }
        
        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Listing</th>
                        <th>Price</th>
                        <th>Components</th>
                        <th>Score</th>
                        <th>Location</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        data.listings.forEach(item => {
            // Build components summary (2-column grid: CPU+GPU top, RAM+SSD bottom)
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
                const ramMatch = item.ram_match_method.match(/(\d+)\s*GB/i);
                if (ramMatch) ramCapacity = parseInt(ramMatch[1]);
            }
            if (ramCapacity) {
                compRam = `<div class="comp-row"><span class="comp-tag comp-ram">RAM</span><span class="comp-name">${ramCapacity}GB ${item.ram_type || ''}</span></div>`;
            }
            let ssdCapacity = item.ssd_capacity;
            if (!ssdCapacity && item.ssd_match_method) {
                const ssdMatch = item.ssd_match_method.match(/(\d+)\s*GB/i);
                if (ssdMatch) ssdCapacity = parseInt(ssdMatch[1]);
            }
            if (ssdCapacity) {
                compSsd = `<div class="comp-row"><span class="comp-tag comp-ssd">SSD</span><span class="comp-name">${ssdCapacity}GB</span></div>`;
            }
            const anyComp = compCpu || compGpu || compRam || compSsd;
            const componentsHtml = anyComp
                ? `<div class="comp-grid">${compCpu}${compGpu}${compRam}${compSsd}</div>`
                : '<em class="no-components">No components detected</em>';

            // Use backend prebuilt flag
            const isPrebuilt = Boolean(item.is_prebuilt);
            const pcType = item.pc_type || (isPrebuilt ? 'prebuilt' : 'custom');
            const pcTypeChip = isPrebuilt
                ? '<span class="pc-type-chip prebuilt">🏭 Prebuilt</span>'
                : '<span class="pc-type-chip custom">🛠️ Custom</span>';
            const cleanTitle = cleanComputerTitle(item.title) || (isPrebuilt ? 'Prebuilt PC' : 'Custom PC');
            
            // Image - escape special chars for onclick
            const rawImageUrl = item.image_url ? item.image_url : '';
            const fullImageUrl = rawImageUrl
                .replace(/\.t\./, '.800.')
                .replace(/\.th\./, '.')
                .replace(/\.thumb\./, '.')
                .replace(/\/thumb\//, '/');
            const safeImageUrl = fullImageUrl.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const safeTitle = (item.title || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const safeListingId = item.listing_id ? item.listing_id.replace(/'/g, "\\'") : '';
            
            const imageHtml = fullImageUrl 
                ? `<div class="listing-image-wrapper">
                    <img src="${fullImageUrl}" alt="Computer" class="listing-thumb" loading="lazy" onclick="event.stopPropagation(); showImageModal('${safeImageUrl}', '${safeTitle}')">
                    ${item.prebuilt_badge ? `<div class="prebuilt-overlay">${item.prebuilt_badge}</div>` : ''}
                   </div>`
                : '<div class="listing-thumb-placeholder">💻</div>';
            
            // Debug info tooltip
            const debugInfo = item.is_prebuilt ? `title="Prebuilt: ${item.is_prebuilt}, Boring: ${item.is_boring}"` : '';
            
            html += `
                <tr class="clickable ${pcType}-row" onclick="showComputerDetail('${safeListingId}')">
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
            `;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
        
    } catch (error) {
        document.getElementById('listings-container').innerHTML = 
            `<div class="error">Failed to load listings: ${error.message}</div>`;
    }
}

async function showComputerDetail(listingId) {
    console.log('Opening computer detail for:', listingId);
    currentListingId = listingId;
    currentListingTitle = '';
    
    try {
        const response = await fetch(`/api/computers/${listingId}`);
        const data = await response.json();
        
        if (!data.success) {
            console.error('Error:', data.error);
            document.getElementById('computer-content').innerHTML = 
                `<div class="error" style="padding: 2rem;"><strong>API Error:</strong><br>${data.error || 'Unknown error'}</div>`;
            document.getElementById('computer-modal').classList.add('active');
            return;
        }
        
        const listing = data.listing;
        const breakdown = data.breakdown;
        
        currentListingTitle = listing.title || 'Computer Details';
        document.getElementById('computer-title').textContent = currentListingTitle;
        
        // Reset flag button
        const flagBtn = document.getElementById('flag-listing-btn');
        flagBtn.textContent = '🚩 Flag';
        flagBtn.style.background = '#dc3545';
        flagBtn.disabled = false;
        
        // Build detailed component sections
        const componentsHtml = buildComponentsSection(breakdown);
        const priceAnalysisHtml = buildPriceAnalysis(breakdown, listing);
        const listingInfoHtml = buildListingInfo(listing);
        const priceHistoryHtml = await buildPriceHistory(listingId);
        const rawDescriptionHtml = buildRawDescription(listing);
        const specsHtml = buildFullSpecs(listing, breakdown);
        
        // Image HTML - use larger image
        const rawImageUrl = listing.image_url || '';
        const fullImageUrl = rawImageUrl
            .replace(/\.t\./, '.800.')
            .replace(/\.th\./, '.')
            .replace(/\.thumb\./, '.')
            .replace(/\/thumb\//, '/');
        const imageHtml = fullImageUrl
            ? `<div class="computer-image-container">
                <img src="${fullImageUrl}" alt="Computer" class="computer-main-image" onclick="showImageModal('${fullImageUrl.replace(/'/g, "\\'")}', '${(listing.title || '').replace(/'/g, "\\'")}')">
               </div>`
            : '';
        
        let html = `
            <div class="computer-detail-layout">
                <!-- Top Section: Image centered -->
                <div class="computer-image-section">
                    ${imageHtml}
                </div>
                
                <!-- Bottom Section: Two columns -->
                <div class="computer-detail-grid">
                    <!-- Left Column: Description, Listing Info, Price Analysis, Price History -->
                    <div class="detail-column">
                        <div class="detail-section">
                            <h4 class="section-title">📝 Description</h4>
                            ${rawDescriptionHtml}
                        </div>
                        ${listingInfoHtml}
                        ${priceAnalysisHtml}
                        ${priceHistoryHtml}
                    </div>
                    
                    <!-- Right Column: Components & Specs -->
                    <div class="detail-column">
                        <div class="detail-section">
                            <h4 class="section-title">
                                <span class="component-icon cpu-icon">⚙️</span>
                                <span class="component-icon gpu-icon">🎮</span>
                                <span class="component-icon ram-icon">💾</span>
                                <span class="component-icon ssd-icon">💽</span>
                                Detected Components
                            </h4>
                            <div class="components-grid">
                                ${componentsHtml || '<em class="no-components">No components detected</em>'}
                            </div>
                        </div>
                        
                        <!-- Monitor Detection Status -->
                        <div class="detail-section">
                            <div class="monitor-status-indicator ${(breakdown.monitor || breakdown.monitor_included || breakdown.monitor_price || breakdown.fallback_monitor_price) ? 'monitor-detected' : 'monitor-not-detected'}"
                                 title="${(breakdown.monitor || breakdown.monitor_included || breakdown.monitor_price || breakdown.fallback_monitor_price) ? 'Monitor detected in listing' : 'No monitor detected'}"
                            >
                                <span class="monitor-icon">🖥️</span>
                                ${(breakdown.monitor || breakdown.monitor_included || breakdown.monitor_price || breakdown.fallback_monitor_price) 
                                    ? 'Monitor Detected' + (breakdown.monitor?.size ? `: ${breakdown.monitor.size}" ${breakdown.monitor.resolution || ''}` : (breakdown.fallback_monitor_price ? ' (fallback)' : ''))
                                    : 'No Monitor Detected'}
                            </div>
                        </div>
                        
                        ${specsHtml}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('computer-content').innerHTML = html;
        document.getElementById('computer-modal').classList.add('active');
        
        // Reset flagging form when opening modal
        resetFlaggingForm();
        
        // Populate RAM detected size in flag form
        if (breakdown.ram && breakdown.ram.capacity_gb) {
            const ramDetectedSize = document.getElementById('ram-detected-size');
            if (ramDetectedSize) ramDetectedSize.value = breakdown.ram.capacity_gb + 'GB';
        }
        
        // Initialize price chart if data exists
        if (breakdown.price_history && breakdown.price_history.length > 1) {
            renderPriceChart(breakdown.price_history);
        }
        
    } catch (error) {
        console.error('Error loading computer details:', error);
        document.getElementById('computer-content').innerHTML = 
            `<div class="error" style="padding: 2rem;"><strong>Error loading details:</strong><br>${error.message}</div>`;
        document.getElementById('computer-modal').classList.add('active');
    }
}

function buildComponentsSection(breakdown) {
    let html = '';
    
    // CPU
    if (breakdown.cpu) {
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large cpu-icon">⚙️</div>
                    <div class="component-info">
                        <div class="component-name">${breakdown.cpu.producer || ''} ${breakdown.cpu.model}</div>
                        <div class="component-specs">
                            ${breakdown.cpu.processor_number ? `<span class="spec-tag">${breakdown.cpu.processor_number}</span>` : ''}
                            ${breakdown.cpu.cores ? `<span class="spec-tag">${breakdown.cpu.cores} Cores</span>` : ''}
                            ${breakdown.cpu.threads ? `<span class="spec-tag">${breakdown.cpu.threads} Threads</span>` : ''}
                            ${breakdown.cpu.base_freq ? `<span class="spec-tag">${breakdown.cpu.base_freq} GHz</span>` : ''}
                            ${breakdown.cpu.tdp ? `<span class="spec-tag">${breakdown.cpu.tdp}W TDP</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.cpu_avg_price?.toFixed(0) || '?'}</div>
                        ${breakdown.cpu_confidence ? `<div class="confidence-tag">${(breakdown.cpu_confidence * 100).toFixed(0)}%</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    // GPU
    if (breakdown.gpu) {
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large gpu-icon">🎮</div>
                    <div class="component-info">
                        <div class="component-name">${breakdown.gpu.vendor} ${breakdown.gpu.model}</div>
                        <div class="component-specs">
                            ${breakdown.gpu.vram_gb ? `<span class="spec-tag">${breakdown.gpu.vram_gb}GB VRAM</span>` : ''}
                            ${breakdown.gpu.vram_type ? `<span class="spec-tag">${breakdown.gpu.vram_type}</span>` : ''}
                            ${breakdown.gpu.base_clock ? `<span class="spec-tag">${breakdown.gpu.base_clock} MHz</span>` : ''}
                            ${breakdown.gpu.tdp ? `<span class="spec-tag">${breakdown.gpu.tdp}W</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.gpu_avg_price?.toFixed(0) || '?'}</div>
                        ${breakdown.gpu_confidence ? `<div class="confidence-tag">${(breakdown.gpu_confidence * 100).toFixed(0)}%</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    } else if (breakdown.gpu === null || breakdown.gpu === undefined) {
        // No GPU detected - show as Unicorn
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large gpu-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">🦄</div>
                    <div class="component-info">
                        <div class="component-name">Unicorn (No GPU detected)</div>
                        <div class="component-specs">
                            <span class="spec-tag" style="background: #9b59b6; color: white;">🦄 Rare</span>
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">🦄 Unicorn</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // RAM
    if (breakdown.ram) {
        const ramName = breakdown.ram.name || (breakdown.ram.capacity_gb ? breakdown.ram.capacity_gb + 'GB RAM' : 'RAM');
        const ramId = breakdown.ram.ram_id || '';
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large ram-icon">💾</div>
                    <div class="component-info">
                        <div class="component-name">${ramName}</div>
                        <div class="component-specs">
                            ${breakdown.ram.capacity_gb ? `<span class="spec-tag">${breakdown.ram.capacity_gb}GB</span>` : ''}
                            ${breakdown.ram.speed ? `<span class="spec-tag">${breakdown.ram.speed}</span>` : ''}
                            ${breakdown.ram.ram_type ? `<span class="spec-tag">${breakdown.ram.ram_type}</span>` : ''}
                            ${breakdown.ram.match_method && !breakdown.ram.is_matched ? `<span class="spec-tag" style="background: #ffc107; color: #000;">📋 ${breakdown.ram.match_method}</span>` : ''}
                        </div>
                        <!-- RAM Flag Buttons -->
                        <div class="ram-flag-buttons" style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
                            <button class="btn btn-tiny" style="background: #dc3545; color: white; font-size: 0.7rem; padding: 4px 8px;" 
                                onclick="showRamWrongModal('${ramId}', '${ramName.replace(/'/g, "\\'")}')">Wrong</button>
                            <button class="btn btn-tiny" style="background: #6c757d; color: white; font-size: 0.7rem; padding: 4px 8px;" 
                                onclick="flagRamSkip('${ramId}')">Skip</button>
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.ram_avg_price?.toFixed(0) || '?'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Motherboard (Generic Detection)
    if (breakdown.motherboard) {
        const mb = breakdown.motherboard;
        const chipsetList = mb.supported_chipsets ? mb.supported_chipsets.slice(0, 4).join(', ') + (mb.supported_chipsets.length > 4 ? '...' : '') : '';
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large" style="background: #8e44ad;">🔌</div>
                    <div class="component-info">
                        <div class="component-name">${mb.name || 'Motherboard'}</div>
                        <div class="component-specs">
                            ${mb.socket ? `<span class="spec-tag">${mb.socket}</span>` : ''}
                            ${chipsetList ? `<span class="spec-tag" title="${mb.supported_chipsets?.join(', ') || ''}">Chipsets: ${chipsetList}</span>` : ''}
                            ${mb.is_generic ? '<span class="spec-tag" style="background: #f39c12; color: #000;">📋 Generic</span>' : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.motherboard_avg_price?.toFixed(0) || '?'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Storage drives
    ['ssd', 'ssd2', 'ssd3'].forEach((key, idx) => {
        if (breakdown[key]) {
            const drive = breakdown[key];
            const label = idx === 0 ? 'SSD' : idx === 1 ? 'SSD (2nd)' : 'SSD (3rd)';
            html += `
                <div class="component-row detailed">
                    <div class="component-header">
                        <div class="component-icon-large ssd-icon">💽</div>
                        <div class="component-info">
                            <div class="component-name">${label}: ${drive.brand || ''} ${drive.model || drive.name || 'Drive'}</div>
                            <div class="component-specs">
                                ${drive.capacity_gb ? `<span class="spec-tag">${drive.capacity_gb}GB</span>` : ''}
                                ${drive.interface ? `<span class="spec-tag">${drive.interface}</span>` : ''}
                                ${drive.form_factor ? `<span class="spec-tag">${drive.form_factor}</span>` : ''}
                                ${drive.nand_type ? `<span class="spec-tag">${drive.nand_type}</span>` : ''}
                            </div>
                        </div>
                        <div class="component-value">
                            <div class="price-tag">~€${breakdown[key + '_avg_price']?.toFixed(0) || '?'}</div>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    // PSU
    if (breakdown.psu) {
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large psu-icon">🔌</div>
                    <div class="component-info">
                        <div class="component-name">PSU: ${breakdown.psu.name || 'Power Supply'}</div>
                        <div class="component-specs">
                            ${breakdown.psu.wattage ? `<span class="spec-tag">${breakdown.psu.wattage}W</span>` : ''}
                            ${breakdown.psu.modular ? `<span class="spec-tag">${breakdown.psu.modular}</span>` : ''}
                            ${breakdown.psu.efficiency ? `<span class="spec-tag">${breakdown.psu.efficiency}</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.psu_avg_price?.toFixed(0) || '?'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Case
    if (breakdown.case) {
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large case-icon">🖥️</div>
                    <div class="component-info">
                        <div class="component-name">Case: ${breakdown.case.name || 'PC Case'}</div>
                        <div class="component-specs">
                            ${breakdown.case.type ? `<span class="spec-tag">${breakdown.case.type}</span>` : ''}
                            ${breakdown.case.form_factor ? `<span class="spec-tag">${breakdown.case.form_factor}</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.case_avg_price?.toFixed(0) || '?'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Motherboard
    if (breakdown.motherboard) {
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large motherboard-icon">🔧</div>
                    <div class="component-info">
                        <div class="component-name">Motherboard: ${breakdown.motherboard.name || 'Unknown'}</div>
                        <div class="component-specs">
                            ${breakdown.motherboard.socket ? `<span class="spec-tag">${breakdown.motherboard.socket}</span>` : ''}
                            ${breakdown.motherboard.chipset ? `<span class="spec-tag">${breakdown.motherboard.chipset}</span>` : ''}
                            ${breakdown.motherboard.form_factor ? `<span class="spec-tag">${breakdown.motherboard.form_factor}</span>` : ''}
                            ${breakdown.motherboard.ram_slots ? `<span class="spec-tag">${breakdown.motherboard.ram_slots} RAM Slots</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${breakdown.motherboard_price?.toFixed(0) || '?'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Monitor
    if (breakdown.monitor || breakdown.monitor_included || breakdown.monitor_price || breakdown.fallback_monitor_price) {
        const monitorName = breakdown.monitor?.name || (breakdown.fallback_monitor_price ? 'Monitor detected (fallback)' : 'Monitor included');
        const monitorSize = breakdown.monitor?.size || '';
        const monitorResolution = breakdown.monitor?.resolution || '';
        const monitorPrice = breakdown.monitor_price || breakdown.fallback_monitor_price || 100;
        
        html += `
            <div class="component-row detailed">
                <div class="component-header">
                    <div class="component-icon-large monitor-icon">🖥️</div>
                    <div class="component-info">
                        <div class="component-name">${monitorName}</div>
                        <div class="component-specs">
                            ${monitorSize ? `<span class="spec-tag">${monitorSize}"</span>` : ''}
                            ${monitorResolution ? `<span class="spec-tag">${monitorResolution}</span>` : ''}
                            ${breakdown.monitor?.refresh_rate ? `<span class="spec-tag">${breakdown.monitor.refresh_rate}Hz</span>` : ''}
                            ${breakdown.monitor?.panel_type ? `<span class="spec-tag">${breakdown.monitor.panel_type}</span>` : ''}
                        </div>
                    </div>
                    <div class="component-value">
                        <div class="price-tag">~€${monitorPrice.toFixed(0)}</div>
                        ${breakdown.monitor_confidence ? `<div class="confidence-tag">${(breakdown.monitor_confidence * 100).toFixed(0)}%</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    return html;
}

function buildPriceAnalysis(breakdown, listing) {
    if (!breakdown.grand_total) return '';
    
    const priceDiff = (listing.price_eur || 0) - (breakdown.grand_total || 0);
    const isGoodDeal = priceDiff < 0;
    const diffPercent = breakdown.grand_total > 0 
        ? Math.abs(priceDiff / breakdown.grand_total * 100).toFixed(1) 
        : 0;
    
    const breakdownId = 'price-analysis-' + Math.random().toString(36).substr(2, 9);
    
    return `
        <div class="detail-section price-analysis ${isGoodDeal ? 'good-deal' : 'overpriced'}" id="${breakdownId}">
            <div class="price-analysis-header">
                <h4 class="section-title">💰 Price Analysis</h4>
                <label class="toggle-summary-label">
                    <input type="checkbox" id="${breakdownId}-toggle" checked onchange="toggleSummaryFields('${breakdownId}')">
                    <span>Show summary</span>
                </label>
            </div>
            <div class="price-comparison">
                <div class="price-item">
                    <div class="price-label">Listing Price</div>
                    <div class="price-value main">€${listing.price_eur?.toFixed(2) || '0'}</div>
                </div>
                <div class="price-arrow">→</div>
                <div class="price-item">
                    <div class="price-label">Component Value</div>
                    <div class="price-value estimate">€${breakdown.grand_total?.toFixed(2) || '0'}</div>
                </div>
            </div>
            <div class="deal-verdict ${isGoodDeal ? 'positive' : 'negative'}">
                <div class="verdict-icon">${isGoodDeal ? '👍' : '👎'}</div>
                <div class="verdict-text">
                    <strong>${isGoodDeal ? 'Good Deal!' : 'Overpriced'}</strong>
                    <div class="verdict-sub">
                        ${isGoodDeal ? 'Cheaper' : 'More expensive'} by €${Math.abs(priceDiff).toFixed(0)} 
                        (${diffPercent}% ${isGoodDeal ? 'below' : 'above'} component value)
                    </div>
                </div>
            </div>
            <div class="price-breakdown summary-fields">
                <div class="breakdown-row">
                    <span>Detected components:</span>
                    <span>€${breakdown.detected_total?.toFixed(0) || '0'}</span>
                </div>
                <div class="breakdown-row">
                    <span>Estimated missing:</span>
                    <span>€${breakdown.fallback_total?.toFixed(0) || '0'}</span>
                </div>
                <div class="breakdown-row">
                    <span>Component price (value):</span>
                    <span>€${breakdown.grand_total?.toFixed(0)}</span>
                </div>
                <div class="breakdown-row total">
                    <span>Total estimated value:</span>
                    <span>€${breakdown.grand_total?.toFixed(0)}</span>
                </div>
            </div>
        </div>
    `;
}

function toggleSummaryFields(breakdownId) {
    const checkbox = document.getElementById(breakdownId + '-toggle');
    const section = document.getElementById(breakdownId);
    if (checkbox && section) {
        const summaryFields = section.querySelectorAll('.price-breakdown, .deal-verdict');
        summaryFields.forEach(el => {
            el.style.display = checkbox.checked ? '' : 'none';
        });
    }
}

async function buildPriceHistory(listingId) {
    try {
        const response = await fetch(`/api/price-history/${listingId}`);
        const data = await response.json();
        
        if (!data.history || data.history.length < 2) {
            return `
                <div class="detail-section">
                    <h4 class="section-title">📈 Price History</h4>
                    <div class="no-data">No price history available</div>
                </div>
            `;
        }
        
        const history = data.history;
        const currentPrice = history[0].price_eur;
        const firstPrice = history[history.length - 1].price_eur;
        const priceChange = currentPrice - firstPrice;
        const changePercent = firstPrice > 0 ? (priceChange / firstPrice * 100).toFixed(1) : 0;
        
        let changesHtml = '';
        for (let i = 0; i < history.length - 1; i++) {
            const current = history[i];
            const prev = history[i + 1];
            const change = current.price_eur - prev.price_eur;
            if (Math.abs(change) > 0.01) {
                const changeClass = change < 0 ? 'decrease' : 'increase';
                const arrow = change < 0 ? '↓' : '↑';
                changesHtml += `
                    <div class="price-change-row ${changeClass}">
                        <span>${new Date(current.recorded_at).toLocaleDateString()}</span>
                        <span>${arrow} €${Math.abs(change).toFixed(2)}</span>
                    </div>
                `;
            }
        }
        
        return `
            <div class="detail-section">
                <h4 class="section-title">📈 Price History</h4>
                <div class="price-history-summary">
                    <div class="history-stat">
                        <div class="history-label">First Price</div>
                        <div class="history-value">€${firstPrice.toFixed(2)}</div>
                    </div>
                    <div class="history-stat">
                        <div class="history-label">Current Price</div>
                        <div class="history-value">€${currentPrice.toFixed(2)}</div>
                    </div>
                    <div class="history-stat">
                        <div class="history-label">Total Change</div>
                        <div class="history-value ${priceChange < 0 ? 'positive' : 'negative'}">
                            ${priceChange < 0 ? '↓' : '↑'} €${Math.abs(priceChange).toFixed(2)} (${changePercent}%)
                        </div>
                    </div>
                </div>
                ${changesHtml ? `<div class="price-changes-list">${changesHtml}</div>` : ''}
            </div>
        `;
    } catch (error) {
        console.error('Error loading price history:', error);
        return '';
    }
}

function buildListingInfo(listing) {
    const statusBadge = listing.is_active 
        ? '<span class="status-badge active">Active</span>'
        : '<span class="status-badge inactive">Inactive</span>';
    
    const buildType = listing.build_type || 'custom';
    const buildTypeColors = {
        'custom': '#3498db',
        'prebuilt': '#e74c3c',
        'office': '#f39c12'
    };
    const buildTypeLabels = {
        'custom': '🛠️ Custom Build',
        'prebuilt': '📦 Prebuilt',
        'office': '💼 Office PC'
    };
    const buildTypeBadge = `<span class="status-badge" style="background: ${buildTypeColors[buildType] || '#3498db'}; color: white;">${buildTypeLabels[buildType] || buildType}</span>`;
    
    const isAdminMode = localStorage.getItem('adminMode') === 'true';
    
    return `
        <div class="detail-section">
            <h4 class="section-title">📋 Listing Information</h4>
            <div class="info-grid">
                <div class="info-row">
                    <span class="info-label">Listing ID</span>
                    <span class="info-value mono">${listing.listing_id || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Status</span>
                    <span class="info-value">${statusBadge}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Build Type</span>
                    <span class="info-value">${buildTypeBadge}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Toggle Status</span>
                    <span class="info-value">
                        <label class="toggle-label">
                            <input type="checkbox" ${buildType === 'prebuilt' ? 'checked' : ''} 
                                onchange="togglePrebuiltStatus('${listing.listing_id}', this.checked)">
                            <span>Mark as Prebuilt</span>
                        </label>
                    </span>
                </div>
                ${isAdminMode ? `
                <div class="info-row">
                    <span class="info-label">Admin: Change Type</span>
                    <span class="info-value">
                        <select id="prebuilt-toggle-${listing.listing_id}" class="admin-select" onchange="updatePrebuiltStatus('${listing.listing_id}', this.value)">
                            <option value="custom" ${buildType === 'custom' ? 'selected' : ''}>Custom Build</option>
                            <option value="prebuilt" ${buildType === 'prebuilt' ? 'selected' : ''}>Prebuilt</option>
                            <option value="office" ${buildType === 'office' ? 'selected' : ''}>Office PC</option>
                        </select>
                    </span>
                </div>
                ` : ''}
                <div class="info-row">
                    <span class="info-label">Price</span>
                    <span class="info-value price">€${listing.price_eur?.toFixed(2) || '0'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Location</span>
                    <span class="info-value">${listing.seller_location || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">First Seen</span>
                    <span class="info-value">${listing.first_seen_at ? new Date(listing.first_seen_at).toLocaleString() : 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Last Updated</span>
                    <span class="info-value">${listing.last_seen_at ? new Date(listing.last_seen_at).toLocaleString() : 'N/A'}</span>
                </div>
                ${listing.original_listing_id ? `
                <div class="info-row">
                    <span class="info-label">Original ID</span>
                    <span class="info-value">${listing.original_listing_id}</span>
                </div>
                ` : ''}
            </div>
            <div class="action-buttons">
                <a href="${listing.listing_url || '#' }" target="_blank" class="btn">🔗 View on ss.com</a>
                <button class="btn btn-secondary" onclick="copyToClipboard('${listing.listing_url}')">📋 Copy Link</button>
            </div>
        </div>
    `;
}

function buildRawDescription(listing) {
    if (!listing.description && !listing.title) return '';
    
    return `
        <div class="description-box">
            <div class="description-content">${listing.description ? listing.description.replace(/\n/g, '<br>') : listing.title}</div>
        </div>
    `;
}

function buildFullSpecs(listing, breakdown) {
    const specs = [];
    
    if (breakdown.cpu?.cores) specs.push({ label: 'CPU Cores', value: breakdown.cpu.cores });
    if (breakdown.cpu?.threads) specs.push({ label: 'CPU Threads', value: breakdown.cpu.threads });
    if (breakdown.cpu?.base_freq) specs.push({ label: 'CPU Base Clock', value: breakdown.cpu.base_freq + ' GHz' });
    if (breakdown.cpu?.boost_freq) specs.push({ label: 'CPU Boost Clock', value: breakdown.cpu.boost_freq + ' GHz' });
    if (breakdown.gpu?.vram_gb) specs.push({ label: 'GPU VRAM', value: breakdown.gpu.vram_gb + ' GB' });
    if (breakdown.gpu?.base_clock) specs.push({ label: 'GPU Clock', value: breakdown.gpu.base_clock + ' MHz' });
    if (breakdown.ram?.capacity_gb) specs.push({ label: 'Total RAM', value: breakdown.ram.capacity_gb + ' GB' });
    if (breakdown.ram?.speed) specs.push({ label: 'RAM Speed', value: breakdown.ram.speed });
    
    const totalStorage = (breakdown.ssd?.capacity_gb || 0) + (breakdown.ssd2?.capacity_gb || 0) + (breakdown.ssd3?.capacity_gb || 0);
    if (totalStorage > 0) specs.push({ label: 'Total Storage', value: totalStorage + ' GB' });
    if (breakdown.psu?.wattage) specs.push({ label: 'PSU Wattage', value: breakdown.psu.wattage + 'W' });
    
    if (specs.length === 0) return '';
    
    const specsHtml = specs.map(s => `
        <div class="spec-row">
            <span class="spec-label">${s.label}</span>
            <span class="spec-value">${s.value}</span>
        </div>
    `).join('');
    
    return `
        <div class="detail-section">
            <h4 class="section-title">⚙️ System Specifications</h4>
            <div class="specs-grid">
                ${specsHtml}
            </div>
        </div>
    `;
}

function closeComputerModal() {
    document.getElementById('computer-modal').classList.remove('active');
}

function showImageModal(imageUrl, title) {
    const fullImageUrl = imageUrl
        .replace(/\.t\./, '.800.')
        .replace(/\.th\./, '.')
        .replace(/\.thumb\./, '.')
        .replace(/\/thumb\//, '/');
    document.getElementById('preview-image').src = fullImageUrl;
    document.getElementById('preview-image').alt = title;
    document.getElementById('preview-title').textContent = title;
    document.getElementById('image-preview-modal').classList.add('active');
}

function closeImageModal() {
    document.getElementById('image-preview-modal').classList.remove('active');
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Link copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Flag category and component selection
function selectFlagCategory(category) {
    document.getElementById('flag-category').value = category;
    
    document.querySelectorAll('.flag-category-btn').forEach(btn => {
        btn.classList.remove('selected');
        if (btn.dataset.category === category) {
            btn.classList.add('selected');
        }
    });
    
    const scraperSection = document.getElementById('scraper-components-section');
    if (category === 'SCRAPPER') {
        scraperSection.classList.add('visible');
    } else {
        scraperSection.classList.remove('visible');
        // Clear all checkboxes and issue fields
        document.querySelectorAll('.component-issue-checkbox').forEach(cb => {
            cb.checked = false;
        });
        document.querySelectorAll('.component-issue-card').forEach(card => {
            card.classList.remove('selected', 'expanded');
        });
        document.querySelectorAll('.component-issue-body').forEach(body => {
            body.style.display = 'none';
        });
        // Clear all issue text inputs
        ['motherboard', 'cpu', 'gpu', 'ram', 'ssd'].forEach(comp => {
            const input = document.getElementById(`${comp}-issue-text`);
            if (input) input.value = '';
        });
        document.getElementById('motherboard-correct-id').value = '';
    }
    
    updateFlagMessage();
    updateFlagButtonState();
}

function toggleComponentIssue(component) {
    const card = document.querySelector(`.component-issue-card[data-component="${component}"]`);
    const checkbox = document.getElementById(`cb-${component}`);
    const body = document.getElementById(`${component}-issue-body`);
    
    // Toggle checkbox
    checkbox.checked = !checkbox.checked;
    
    if (checkbox.checked) {
        card.classList.add('selected', 'expanded');
        body.style.display = 'block';
    } else {
        card.classList.remove('selected', 'expanded');
        body.style.display = 'none';
    }
    
    updateFlagMessage();
    updateFlagButtonState();
}

// Legacy function - keep for compatibility but make it call the new function
function toggleComponent(component) {
    toggleComponentIssue(component);
}

function updateFlagMessage() {
    const category = document.getElementById('flag-category').value;
    const previewDiv = document.getElementById('flag-message-preview');
    const messageText = document.getElementById('flag-message-text');
    const extraComment = document.getElementById('flag-comment').value.trim();
    
    if (!category) {
        previewDiv.classList.remove('visible');
        return;
    }
    
    let message = '';
    
    if (category === 'SCRAPPER') {
        const componentMessages = [];
        const components = ['motherboard', 'cpu', 'gpu', 'ram', 'ssd'];
        
        components.forEach(comp => {
            const checkbox = document.getElementById(`cb-${comp}`);
            if (checkbox && checkbox.checked) {
                // Special handling for RAM with size fields
                if (comp === 'ram') {
                    const detectedSize = document.getElementById('ram-detected-size')?.value.trim();
                    const correctSize = document.getElementById('ram-correct-size')?.value.trim();
                    const issueText = document.getElementById(`${comp}-issue-text`)?.value.trim();
                    
                    let ramMessage = 'RAM: ';
                    if (detectedSize && correctSize) {
                        ramMessage += `Scrapper scrapped ${detectedSize}, should have been ${correctSize}`;
                    } else if (issueText) {
                        ramMessage += issueText;
                    } else {
                        ramMessage += 'match incorrect';
                    }
                    componentMessages.push(ramMessage);
                } else {
                    const issueText = document.getElementById(`${comp}-issue-text`)?.value.trim();
                    if (issueText) {
                        componentMessages.push(`${comp.toUpperCase()}: ${issueText}`);
                    } else {
                        componentMessages.push(`${comp.toUpperCase()}: match incorrect`);
                    }
                }
            }
        });
        
        // Add motherboard ID if provided
        const mbCheckbox = document.getElementById('cb-motherboard');
        if (mbCheckbox && mbCheckbox.checked) {
            const mbId = document.getElementById('motherboard-correct-id')?.value.trim();
            if (mbId) {
                const idx = componentMessages.findIndex(m => m.startsWith('MOTHERBOARD:'));
                if (idx >= 0) {
                    componentMessages[idx] += ` (should be ID ${mbId})`;
                }
            }
        }
        
        if (componentMessages.length > 0) {
            message = componentMessages.join('; ');
        }
    } else if (category === 'SELLER') {
        message = 'Seller issue reported';
    } else if (category === 'OTHER') {
        message = 'Other issue reported';
    }
    
    if (extraComment) {
        if (message) {
            message += ' | Additional: ' + extraComment;
        } else {
            message = extraComment;
        }
    }
    
    if (message) {
        messageText.textContent = message;
        previewDiv.classList.add('visible');
    } else {
        previewDiv.classList.remove('visible');
    }
}

function updateFlagButtonState() {
    const category = document.getElementById('flag-category').value;
    const flagBtn = document.getElementById('flag-listing-btn');
    
    let canFlag = false;
    
    if (category === 'SCRAPPER') {
        // Check if any component checkbox is checked
        const checkboxes = document.querySelectorAll('.component-issue-checkbox');
        canFlag = Array.from(checkboxes).some(cb => cb.checked);
    } else if (category === 'SELLER' || category === 'OTHER') {
        canFlag = true;
    }
    
    flagBtn.disabled = !canFlag;
}

function resetFlaggingForm() {
    const flagCategory = document.getElementById('flag-category');
    if (flagCategory) flagCategory.value = '';
    
    document.querySelectorAll('.flag-category-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    // Clear all component checkboxes and issue fields
    document.querySelectorAll('.component-issue-checkbox').forEach(cb => {
        cb.checked = false;
    });
    document.querySelectorAll('.component-issue-card').forEach(card => {
        card.classList.remove('selected', 'expanded');
    });
    document.querySelectorAll('.component-issue-body').forEach(body => {
        body.style.display = 'none';
    });
    ['motherboard', 'cpu', 'gpu', 'ram', 'ssd'].forEach(comp => {
        const input = document.getElementById(`${comp}-issue-text`);
        if (input) input.value = '';
    });
    const mbCorrectId = document.getElementById('motherboard-correct-id');
    if (mbCorrectId) mbCorrectId.value = '';
    
    const scraperSection = document.getElementById('scraper-components-section');
    if (scraperSection) scraperSection.classList.remove('visible');
    
    const flagComment = document.getElementById('flag-comment');
    if (flagComment) flagComment.value = '';
    
    const flagPreview = document.getElementById('flag-message-preview');
    if (flagPreview) flagPreview.classList.remove('visible');
    
    const flagMessageText = document.getElementById('flag-message-text');
    if (flagMessageText) flagMessageText.textContent = '';
    
    const flagBtn = document.getElementById('flag-listing-btn');
    const btnIcon = document.getElementById('flag-btn-icon');
    const btnText = document.getElementById('flag-btn-text');
    if (flagBtn) {
        if (btnIcon) btnIcon.textContent = '🚩';
        if (btnText) btnText.textContent = 'Flag Listing';
        flagBtn.classList.remove('flagged');
        flagBtn.style.background = '#dc3545';
        flagBtn.disabled = true;
    }
}

async function flagCurrentListing() {
    if (!currentListingId) {
        alert('No listing selected');
        return;
    }
    
    const category = document.getElementById('flag-category').value;
    const extraComment = document.getElementById('flag-comment').value.trim();
    
    if (!category) {
        alert('Please select a flag category');
        return;
    }
    
    if (category === 'SCRAPPER') {
        const checkboxes = document.querySelectorAll('.component-issue-checkbox');
        const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
        if (!anyChecked) {
            alert('Please select at least one component for Scraper issues');
            return;
        }
    }
    
    // Build flag message from component issue fields
    let flagMessage = '';
    
    if (category === 'SCRAPPER') {
        const componentMessages = [];
        const components = ['motherboard', 'cpu', 'gpu', 'ram', 'ssd'];
        
        components.forEach(comp => {
            const checkbox = document.getElementById(`cb-${comp}`);
            if (checkbox && checkbox.checked) {
                // Special handling for RAM with size fields
                if (comp === 'ram') {
                    const detectedSize = document.getElementById('ram-detected-size')?.value.trim();
                    const correctSize = document.getElementById('ram-correct-size')?.value.trim();
                    const issueText = document.getElementById(`${comp}-issue-text`)?.value.trim();
                    
                    let ramMessage = 'RAM: ';
                    if (detectedSize && correctSize) {
                        ramMessage += `Scrapper scrapped ${detectedSize}, should have been ${correctSize}`;
                    } else if (issueText) {
                        ramMessage += issueText;
                    } else {
                        ramMessage += 'match incorrect';
                    }
                    componentMessages.push(ramMessage);
                } else {
                    const issueText = document.getElementById(`${comp}-issue-text`)?.value.trim();
                    if (issueText) {
                        componentMessages.push(`${comp.toUpperCase()}: ${issueText}`);
                    } else {
                        componentMessages.push(`${comp.toUpperCase()}: match incorrect`);
                    }
                }
            }
        });
        
        // Add motherboard ID if provided
        const mbCheckbox = document.getElementById('cb-motherboard');
        if (mbCheckbox && mbCheckbox.checked) {
            const mbId = document.getElementById('motherboard-correct-id')?.value.trim();
            if (mbId) {
                const idx = componentMessages.findIndex(m => m.startsWith('MOTHERBOARD:'));
                if (idx >= 0) {
                    componentMessages[idx] += ` (should be ID ${mbId})`;
                }
            }
        }
        
        flagMessage = componentMessages.join('; ');
    } else if (category === 'SELLER') {
        flagMessage = 'Seller issue reported';
    } else if (category === 'OTHER') {
        flagMessage = 'Other issue reported';
    }
    
    if (extraComment) {
        if (flagMessage) {
            flagMessage += ' | Additional: ' + extraComment;
        } else {
            flagMessage = extraComment;
        }
    }
    
    if (!flagMessage) {
        alert('Please enter a reason for flagging');
        return;
    }
    
    try {
        const response = await fetch('/api/flag-listing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                listing_id: currentListingId,
                comment: flagMessage,
                category: 'computer',
                flag_category: category
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Change button status instead of showing popup
            const btn = document.getElementById('flag-listing-btn');
            const btnIcon = document.getElementById('flag-btn-icon');
            const btnText = document.getElementById('flag-btn-text');
            
            btnIcon.textContent = '✓';
            btnText.textContent = 'Flagged';
            btn.classList.add('flagged');
            btn.style.background = '#28a745';
            btn.disabled = true;
            
            setTimeout(() => {
                loadComputers();
                document.getElementById('computer-modal').classList.remove('active');
            }, 1500);
        } else {
            alert('Error: ' + (data.error || 'Failed to flag listing'));
        }
    } catch (error) {
        console.error('Error flagging listing:', error);
        alert('Failed to flag listing. See console for details.');
    }
}

// Toggle flag section collapse
function toggleFlagSection() {
    const section = document.getElementById('flag-section');
    const btn = document.getElementById('flag-toggle-btn');
    
    if (section.classList.contains('collapsed')) {
        section.classList.remove('collapsed');
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M7 14l5-5 5 5z"/></svg>';
    } else {
        section.classList.add('collapsed');
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M7 10l5 5 5-5z"/></svg>';
    }
}

// Auto-resize textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Component Filters Functions
let componentFiltersExpanded = false;

function toggleComponentFilters() {
    const content = document.getElementById('component-filters-content');
    const btn = document.getElementById('toggle-filters-btn');
    
    if (componentFiltersExpanded) {
        content.classList.remove('visible');
        btn.textContent = '▼ Expand';
    } else {
        content.classList.add('visible');
        btn.textContent = '▲ Collapse';
    }
    componentFiltersExpanded = !componentFiltersExpanded;
}

function applyComponentFilters() {
    const cpuBrand = document.getElementById('filter-cpu-brand')?.value || '';
    const cpuCores = document.getElementById('filter-cpu-cores')?.value || '';
    const gpuBrand = document.getElementById('filter-gpu-brand')?.value || '';
    const gpuVram = document.getElementById('filter-gpu-vram')?.value || '';
    const ramCapacity = document.getElementById('filter-ram-capacity')?.value || '';
    const ramDdr = document.getElementById('filter-ram-ddr')?.value || '';
    const ssdTotal = document.getElementById('filter-ssd-total')?.value || '';
    const ssdInterface = document.getElementById('filter-ssd-interface')?.value || '';
    const psuWattage = document.getElementById('filter-psu-wattage')?.value || '';
    const priceMax = document.getElementById('filter-price-max')?.value || '';
    const hasCpu = document.getElementById('filter-has-cpu')?.checked || false;
    const hasGpu = document.getElementById('filter-has-gpu')?.checked || false;
    const hasRam = document.getElementById('filter-has-ram')?.checked || false;
    const hasSsd = document.getElementById('filter-has-ssd')?.checked || false;
    const pcType = document.getElementById('filter-pc-type')?.value || '';
    
    let activeCount = 0;
    if (cpuBrand) activeCount++;
    if (cpuCores) activeCount++;
    if (gpuBrand) activeCount++;
    if (gpuVram) activeCount++;
    if (ramCapacity) activeCount++;
    if (ramDdr) activeCount++;
    if (ssdTotal) activeCount++;
    if (ssdInterface) activeCount++;
    if (psuWattage) activeCount++;
    if (priceMax) activeCount++;
    if (hasCpu) activeCount++;
    if (hasGpu) activeCount++;
    if (hasRam) activeCount++;
    if (hasSsd) activeCount++;
    if (pcType) activeCount++;
    
    const countDisplay = document.getElementById('active-filters-count');
    if (countDisplay) {
        countDisplay.textContent = activeCount > 0 ? `${activeCount} filter(s) active` : '';
        countDisplay.classList.toggle('visible', activeCount > 0);
    }
    
    const rows = document.querySelectorAll('#listings-container tbody tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length < 5) return;
        
        const componentsCell = cells[4].textContent.toLowerCase();
        const priceText = cells[3].textContent;
        const price = parseFloat(priceText.replace('€', '').replace(',', '')) || 0;
        
        let show = true;
        
        if (cpuBrand && !componentsCell.includes(`cpu: ${cpuBrand.toLowerCase()}`)) show = false;
        if (gpuBrand && !componentsCell.includes(`gpu: ${gpuBrand.toLowerCase()}`)) show = false;
        
        if (ramCapacity) {
            const ramBadge = row.querySelector('.badge-ram');
            const ramAttr = ramBadge?.dataset.ramCapacity;
            if (ramAttr) {
                if (parseInt(ramAttr) !== parseInt(ramCapacity)) show = false;
            } else {
                // No RAM info means it cannot match the requested capacity
                show = false;
            }
        }
        
        if (ramDdr) {
            const ramBadge = row.querySelector('.badge-ram');
            const ddrAttr = ramBadge?.dataset.ramType || '';
            if (ddrAttr) {
                if (ddrAttr.toLowerCase() !== ramDdr.toLowerCase()) show = false;
            } else {
                show = false;
            }
        }
        
        if (ssdTotal) {
            const ssdMatch = componentsCell.match(/ssd:\s*(\d+)gb/);
            if (ssdMatch) {
                const ssd = parseInt(ssdMatch[1]);
                if (ssd < parseInt(ssdTotal)) show = false;
            } else {
                show = false;
            }
        }
        
        if (priceMax && price > parseInt(priceMax)) show = false;
        
        if (pcType) {
            const hasPrebuilt = componentsCell.includes('prebuilt');
            const hasBoring = componentsCell.includes('boring');
            
            if (pcType === 'custom') {
                if (hasPrebuilt) show = false;
            } else if (pcType === 'prebuilt') {
                if (!hasPrebuilt) show = false;
            } else if (pcType === 'boring') {
                if (!hasBoring) show = false;
            }
        }
        if (hasCpu && !componentsCell.includes('cpu:')) show = false;
        if (hasGpu && !componentsCell.includes('gpu:')) show = false;
        if (hasRam && !componentsCell.includes('ram:')) show = false;
        if (hasSsd && !componentsCell.includes('ssd:')) show = false;
        
        row.style.display = show ? '' : 'none';
    });
}

function resetComponentFilters() {
    document.getElementById('filter-cpu-brand').value = '';
    document.getElementById('filter-cpu-cores').value = '';
    document.getElementById('filter-gpu-brand').value = '';
    document.getElementById('filter-gpu-vram').value = '';
    document.getElementById('filter-ram-capacity').value = '';
    document.getElementById('filter-ram-ddr').value = '';
    document.getElementById('filter-ssd-total').value = '';
    document.getElementById('filter-ssd-interface').value = '';
    document.getElementById('filter-psu-wattage').value = '';
    document.getElementById('filter-price-max').value = '';
    
    document.getElementById('filter-has-cpu').checked = false;
    document.getElementById('filter-has-gpu').checked = false;
    document.getElementById('filter-has-ram').checked = false;
    document.getElementById('filter-has-ssd').checked = false;
    
    const countDisplay = document.getElementById('active-filters-count');
    if (countDisplay) countDisplay.classList.remove('visible');
    
    const rows = document.querySelectorAll('#listings-container tbody tr');
    rows.forEach(row => row.style.display = '');
}

// Update prebuilt status
async function updatePrebuiltStatus(listingId, buildType) {
    try {
        const response = await fetch('/api/update-listing-type', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                listing_id: listingId,
                build_type: buildType,
                category: 'computer'
            })
        });
        
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById(`prebuilt-toggle-${listingId}`);
            select.classList.add('success');
            setTimeout(() => select.classList.remove('success'), 1000);
            showComputerDetail(listingId);
        } else {
            alert('Failed to update: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error updating build type:', error);
        alert('Failed to update build type');
    }
}

// Toggle prebuilt status
async function togglePrebuiltStatus(listingId, isChecked) {
    const buildType = isChecked ? 'prebuilt' : 'custom';
    try {
        const response = await fetch('/api/update-listing-type', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                listing_id: listingId,
                build_type: buildType,
                category: 'computer'
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showComputerDetail(listingId);
        } else {
            alert('Failed to update: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error toggling prebuilt status:', error);
        alert('Failed to update build type');
    }
}

// RAM Flagging Functions
let currentRamId = null;
let currentRamName = '';

function showRamWrongModal(ramId, ramName) {
    currentRamId = ramId;
    currentRamName = ramName;
    document.getElementById('ram-wrong-current').textContent = ramName;
    document.getElementById('ram-correct-id').value = '';
    document.getElementById('ram-wrong-comment').value = '';
    document.getElementById('ram-wrong-modal').classList.add('active');
}

function closeRamWrongModal() {
    document.getElementById('ram-wrong-modal').classList.remove('active');
    currentRamId = null;
    currentRamName = '';
}

async function submitRamWrongFlag() {
    if (!currentListingId) return;
    
    const correctId = document.getElementById('ram-correct-id').value.trim();
    const extraComment = document.getElementById('ram-wrong-comment').value.trim();
    
    let comment = `RAM is incorrect. Matched with: ${currentRamName}`;
    if (correctId) {
        comment += `. Should have matched with ID: ${correctId}`;
    }
    if (extraComment) {
        comment += `. ${extraComment}`;
    }
    
    try {
        const response = await fetch('/api/flag-listing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                listing_id: currentListingId,
                reason: 'ram_wrong_match',
                comment: comment
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('RAM flagged successfully');
            closeRamWrongModal();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error flagging RAM: ' + error.message);
    }
}

async function flagRamSkip(ramId) {
    if (!currentListingId) return;
    
    try {
        const response = await fetch('/api/flag-listing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                listing_id: currentListingId,
                reason: 'ram_skip',
                comment: `Skip this listing entirely - RAM issue (ID: ${ramId})`
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Listing flagged to skip');
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error flagging listing: ' + error.message);
    }
}

// Add Listing Modal Functions
function openAddListingModal() {
    document.getElementById('add-listing-modal').classList.add('active');
    document.getElementById('add-listing-id-input').value = '';
    document.getElementById('add-listing-id-input').focus();
    document.getElementById('add-listing-error').style.display = 'none';
}

function closeAddListingModal() {
    document.getElementById('add-listing-modal').classList.remove('active');
}

async function addListingById() {
    const listingId = document.getElementById('add-listing-id-input').value.trim();
    const errorDiv = document.getElementById('add-listing-error');
    
    if (!listingId) {
        errorDiv.textContent = 'Please enter a listing ID';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Close modal and open the listing detail
    closeAddListingModal();
    showComputerDetail(listingId);
}

// Allow Enter key to submit
setTimeout(() => {
    const input = document.getElementById('add-listing-id-input');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addListingById();
            }
        });
    }
}, 100);

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Restore saved toggle states (now pill-based)
    const savedPrebuiltOnly = localStorage.getItem('computersPrebuiltOnly');
    const savedHidePrebuilt = localStorage.getItem('computersHidePrebuilt');
    const savedSortBy = localStorage.getItem('computersSortBy');
    const savedSortOrder = localStorage.getItem('computersSortOrder');

    if (savedPrebuiltOnly === 'true') {
        const btn = document.getElementById('toggle-prebuilt');
        if (btn) { btn.classList.add('on'); btn.classList.add('active'); }
    }
    if (savedHidePrebuilt === 'true') {
        const btn = document.getElementById('toggle-hide-prebuilt');
        if (btn) { btn.classList.add('on'); btn.classList.add('active'); }
    }
    if (savedSortBy !== null) {
        document.getElementById('sort-by').value = savedSortBy;
    }
    if (savedSortOrder !== null) {
        document.getElementById('sort-order').value = savedSortOrder;
    }
    
    // Close modals on outside click
    document.getElementById('computer-modal').addEventListener('click', function(e) {
        if (e.target === this) closeComputerModal();
    });
    
    document.getElementById('image-preview-modal').addEventListener('click', function(e) {
        if (e.target === this) closeImageModal();
    });
    
    // Add listing modal outside click
    document.getElementById('add-listing-modal').addEventListener('click', function(e) {
        if (e.target === this) closeAddListingModal();
    });
    
    // RAM wrong modal outside click
    const ramWrongModal = document.getElementById('ram-wrong-modal');
    if (ramWrongModal) {
        ramWrongModal.addEventListener('click', function(e) {
            if (e.target === this) closeRamWrongModal();
        });
    }
    
    loadStats();
    loadComputers();
});
