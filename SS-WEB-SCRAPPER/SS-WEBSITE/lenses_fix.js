// Lenses page fix - simplified error handling
// Add to lenses.html if needed

// Wrap loadListings with better error handling
const originalLoadListings = loadListings;
loadListings = async function() {
    try {
        await originalLoadListings();
    } catch (error) {
        console.error('Lens loading error:', error);
        document.getElementById('listings-container').innerHTML = 
            `<div class="error">Error loading lenses: ${error.message}. Check browser console for details.</div>`;
    }
};

// Debug helper
async function debugLenses() {
    try {
        const response = await fetch('/api/lenses?active=true');
        const text = await response.text();
        console.log('Raw response:', text.substring(0, 500));
        
        try {
            const data = JSON.parse(text);
            console.log('Parsed data:', data);
        } catch (e) {
            console.error('JSON parse error:', e);
        }
    } catch (error) {
        console.error('Fetch error:', error);
    }
}

// Run debug on load
debugLenses();
