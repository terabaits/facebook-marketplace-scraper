# Add listing detail modal to consoles.html

with open(r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\templates\\consoles.html', 'r', encoding='utf-8') as f:
    content = f.read()

modal_html = """

<!-- Listing Detail Modal -->
<div id="listing-detail-modal" class="modal-overlay">
    <div class="modal" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
        <div class="modal-header">
            <h3 id="listing-detail-title">Listing Details</h3>
            <button class="modal-close" onclick="closeListingDetailModal()">&times;</button>
        </div>
        <div id="listing-detail-content" style="padding: 1.5rem;">
            <div class="loading">Loading listing details...</div>
        </div>
        <div style="padding: 1rem 1.5rem; background: #f8f9fa; border-top: 1px solid #eee; display: flex; gap: 1rem; justify-content: flex-end;">
            <button id="listing-detail-flag-btn" class="btn btn-warning" onclick="toggleFlagFromDetail()">🚫 Flag</button>
            <a id="listing-detail-link" href="#" target="_blank" class="btn">View on ss.com →</a>
        </div>
    </div>
</div>
"""

# Insert before first {% endblock %}
if '{% endblock %}' in content:
    content = content.replace('{% endblock %}', modal_html + '{% endblock %}', 1)
    print('Listing detail modal HTML added!')
else:
    print('ERROR: Could not find {% endblock %} in file')

with open(r'G:\\Github\\SS-WEB-SCRAPPER\\SS-WEBSITE\\templates\\consoles.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
