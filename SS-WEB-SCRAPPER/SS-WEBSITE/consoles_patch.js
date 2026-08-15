// Console Listing Detail Modal Functions
// Add these to the end of consoles.html before </script>

let currentDetailListing = null;

async function showListingDetail(listingId) {
    currentDetailListing = listingId;
    
    try {
        const response = await fetch(`/api/listing-details/${listingId}`);
        const data = await response.json();
        
        if (data.error || !data.current) {
            alert('Error loading listing details');
            return;
        }
        
        const item = data.current;
        
        // Set title
        document.getElementById('listing-detail-title').textContent = item.title || 'Listing Details';
        
        // Build content
        let html = '';
        
        // Image
        if (item.image_url) {
            html += `
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <img src="${item.image_url}" alt="${item.title}" 
                         style="max-width: 100%; max-height: 300px; border-radius: 8px; cursor: pointer;"
                         onclick="showImageModal('${item.image_url}', '${item.title.replace(/'/g, "\\'")}')">
                </div>
            `;
        }
        
        // Info grid
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                    <strong>Price:</strong> <span class="price" style="font-size: 1.25rem;">€${item.price_eur}</span>
                </div>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                    <strong>Location:</strong> ${item.seller_location || 'N/A'}
                </div>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                    <strong>Date:</strong> ${item.date_posted ? new Date(item.date_posted).toLocaleDateString() : 'N/A'}
                </div>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                    <strong>Status:</strong> ${item.is_active ? '<span style="color: #27ae60;">Active</span>' : '<span style="color: #e74c3c;">Inactive</span>'}
                </div>
            </div>
        `;
        
        // Console-specific info
        if (item.console_name) {
            html += `
                <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <strong>Console:</strong> ${item.console_name}<br>
                    ${item.variant_name ? `<strong>Variant:</strong> ${item.variant_name}<br>` : ''}
                    ${item.edition_name ? `<strong>Edition:</strong> ${item.edition_name}<br>` : ''}
                    ${item.is_special_edition ? '<span class="badge" style="background: #f59e0b; color: white;">Special Edition</span>' : ''}
                </div>
            `;
        }
        
        // Description
        html += `
            <div style="margin-bottom: 1rem;">
                <strong>Description:</strong>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-top: 0.5rem; max-height: 200px; overflow-y: auto; white-space: pre-wrap;">
                    ${item.description || '<em>No description</em>'}
                </div>
            </div>
        `;
        
        // Price history
        if (data.history && data.history.length > 0) {
            html += `
                <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Price History</h4>
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            data.history.forEach(h => {
                html += `
                    <tr>
                        <td>${h.recorded_at ? new Date(h.recorded_at).toLocaleDateString() : 'N/A'}</td>
                        <td class="price">€${h.price_eur}</td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
        }
        
        // Flag status
        if (data.flag) {
            html += `
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                    <strong>🚫 Flagged:</strong> ${data.flag.comment || 'No comment'}<br>
                    <small>Flagged on: ${new Date(data.flag.flagged_at).toLocaleDateString()}</small>
                </div>
            `;
        }
        
        document.getElementById('listing-detail-content').innerHTML = html;
        
        // Update link
        document.getElementById('listing-detail-link').href = item.listing_url;
        
        // Update flag button
        const isFlagged = flaggedListings.has(listingId);
        const flagBtn = document.getElementById('listing-detail-flag-btn');
        flagBtn.textContent = isFlagged ? '✓ Unflag' : '🚫 Flag';
        flagBtn.className = isFlagged ? 'btn btn-secondary' : 'btn btn-warning';
        
        // Show modal
        document.getElementById('listing-detail-modal').classList.add('active');
        
    } catch (error) {
        console.error('Error loading listing details:', error);
        alert('Error loading listing details');
    }
}

function closeListingDetailModal() {
    document.getElementById('listing-detail-modal').classList.remove('active');
    currentDetailListing = null;
}

async function toggleFlagFromDetail() {
    if (!currentDetailListing) return;
    
    const isFlagged = flaggedListings.has(currentDetailListing);
    await toggleFlag(currentDetailListing, '', isFlagged);
    
    // Refresh modal
    showListingDetail(currentDetailListing);
}

// Close modal on outside click
document.addEventListener('DOMContentLoaded', () => {
    const detailModal = document.getElementById('listing-detail-modal');
    if (detailModal) {
        detailModal.addEventListener('click', function(e) {
            if (e.target === this) closeListingDetailModal();
        });
    }
});
