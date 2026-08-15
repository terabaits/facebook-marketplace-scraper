/**
 * Facebook Marketplace PC Scraper - Popup Script
 */

// Check backend health on popup open
async function checkHealth() {
  const statusEl = document.getElementById('backend-status');
  statusEl.textContent = 'Checking...';
  
  try {
    const response = await fetch('http://localhost:5001/api/v1/extension/health');
    const data = await response.json();
    
    if (data.status === 'healthy') {
      statusEl.textContent = 'Connected';
      statusEl.className = 'status-value connected';
    } else {
      statusEl.textContent = 'Unhealthy';
      statusEl.className = 'status-value disconnected';
    }
  } catch (error) {
    statusEl.textContent = 'Disconnected';
    statusEl.className = 'status-value disconnected';
  }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
  // Error display element
  const errorDisplay = document.createElement('div');
  errorDisplay.id = 'error-display';
  errorDisplay.style.cssText = 'background:#f8d7da;color:#721c24;padding:10px;border-radius:6px;margin:10px 0;font-size:12px;word-break:break-all;display:none;';
  document.querySelector('.header').after(errorDisplay);
  
  function showError(message) {
    errorDisplay.textContent = message;
    errorDisplay.style.display = 'block';
    errorDisplay.onclick = () => {
      navigator.clipboard.writeText(message);
      errorDisplay.textContent = '✅ Copied to clipboard! Click to copy again.';
      setTimeout(() => errorDisplay.textContent = message, 2000);
    };
    errorDisplay.style.cursor = 'pointer';
    errorDisplay.title = 'Click to copy error';
  }
  
  // Check health button
  const checkBtn = document.getElementById('check-health');
  if (checkBtn) {
    checkBtn.addEventListener('click', checkHealth);
  }
  
  // Scrape current page button
  const scrapeBtn = document.getElementById('scrape-page');
  if (scrapeBtn) {
    scrapeBtn.addEventListener('click', async () => {
      const originalText = scrapeBtn.textContent;
      scrapeBtn.textContent = '⏳ Scraping...';
      scrapeBtn.disabled = true;
      errorDisplay.style.display = 'none';
      
      try {
        // Get the current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab.url.includes('facebook.com')) {
          showError('Error: Not on Facebook page\nCurrent URL: ' + tab.url);
          scrapeBtn.textContent = '❌ Error';
          setTimeout(() => {
            scrapeBtn.textContent = originalText;
            scrapeBtn.disabled = false;
          }, 3000);
          return;
        }
        
        // Try to send message to content script
        try {
          const response = await chrome.tabs.sendMessage(tab.id, { action: 'scrapePage' });
          
          if (response && response.success) {
            scrapeBtn.textContent = '✅ Scraped!';
            setTimeout(() => {
              scrapeBtn.textContent = originalText;
              scrapeBtn.disabled = false;
            }, 2000);
          } else {
            showError('Scrape failed: ' + (response?.error || 'Unknown error'));
            scrapeBtn.textContent = '❌ Failed';
            setTimeout(() => {
              scrapeBtn.textContent = originalText;
              scrapeBtn.disabled = false;
            }, 3000);
          }
        } catch (err) {
          // Content script not loaded - try to inject it
          console.log('Content script not loaded, attempting injection...');
          
          try {
            await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              files: ['content.js']
            });
            
            // Wait a moment for script to initialize
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Try again
            const response = await chrome.tabs.sendMessage(tab.id, { action: 'scrapePage' });
            
            if (response && response.success) {
              scrapeBtn.textContent = '✅ Scraped!';
              setTimeout(() => {
                scrapeBtn.textContent = originalText;
                scrapeBtn.disabled = false;
              }, 2000);
            } else {
              showError('Scrape failed after injection: ' + (response?.error || 'Unknown'));
              scrapeBtn.textContent = '❌ Failed';
              setTimeout(() => {
                scrapeBtn.textContent = originalText;
                scrapeBtn.disabled = false;
              }, 3000);
            }
          } catch (injectionErr) {
            showError('Failed to inject content script:\n' + injectionErr.message);
            scrapeBtn.textContent = '❌ Error';
            setTimeout(() => {
              scrapeBtn.textContent = originalText;
              scrapeBtn.disabled = false;
            }, 3000);
          }
        }
      } catch (error) {
        console.error('Scrape error:', error);
        showError('Connection Error:\n' + error.message + '\n\nMake sure you\'re on a Facebook listing page and the extension is loaded.');
        scrapeBtn.textContent = '❌ Error';
        setTimeout(() => {
          scrapeBtn.textContent = originalText;
          scrapeBtn.disabled = false;
        }, 3000);
      }
    });
  }
  
  // Clear cache button
  const clearBtn = document.getElementById('clear-cache');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: 'clearCache' });
      alert('Cache cleared');
    });
  }
  
  // Initial check
  checkHealth();
});
