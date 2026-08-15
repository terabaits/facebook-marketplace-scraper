/**
 * Facebook Marketplace PC Scraper - Content Script
 * Phase 1: Foundation
 * Version: 1.0.2 - Fixed description extraction with Cyrillic priority
 */

(function() {
  'use strict';

  // Configuration
  const API_URL = 'http://localhost:5001/api/v1/extension';
  const VERSION = '1.0.6';
  const DEBOUNCE_MS = 300;
  const MAX_REQUESTS_PER_MINUTE = 60;

  // State
  let isAnalyzing = false;
  let requestCount = 0;
  let requestResetTime = Date.now();
  let observer = null;
  let debounceTimer = null;

  // ==================== SELECTOR ENGINE ====================

  class SelectorEngine {
    constructor() {
      this.cache = new Map();
      this.version = 1;

      // Multi-layer selector strategies
      this.STRATEGIES = {
        listing: {
          aria: '[role="article"][aria-labelledby]',
          pagelet: '[data-pagelet="BrowseFeed"] > div > div',
          structural: 'div[role="main"] > div > div > div',
          fallback: 'div[class*="x1qjc9v5"]'
        },
        title: {
          aria: '[role="heading"][aria-level="3"]',
          structural: 'h3, h4',
          text: 'span[dir="auto"]'
        },
        price: {
          aria: '[aria-label*="price" i]',
          structural: 'span:first-child',
          pattern: (el) => /[\$\€\£][\d,.]+/.test(el.textContent)
        },
        description: {
          aria: '[aria-label="Description"]',
          structural: 'div > span[dir="auto"]'
        },
        image: {
          aria: '[role="img"]',
          tag: 'img[src*="fbcdn.net"]'
        }
      };
    }

    find(context, type) {
      const cacheKey = `${this.version}:${type}:${context?.className || 'root'}`;

      if (this.cache.has(cacheKey)) {
        return this.cache.get(cacheKey);
      }

      const strategies = this.STRATEGIES[type];
      if (!strategies) {
        console.warn(`[SelectorEngine] Unknown type: ${type}`);
        return null;
      }

      // Try each strategy in order
      for (const [strategy, selector] of Object.entries(strategies)) {
        if (strategy === 'fallback' || strategy === 'pattern') continue;

        try {
          const result = context?.querySelector(selector) || document.querySelector(selector);
          if (result) {
            this.cache.set(cacheKey, result);
            return result;
          }
        } catch (e) {
          // Invalid selector, continue
        }
      }

      // Try pattern-based detection
      if (strategies.pattern) {
        const candidates = context?.querySelectorAll('span, div') || [];
        for (const el of candidates) {
          if (strategies.pattern(el)) {
            this.cache.set(cacheKey, el);
            return el;
          }
        }
      }

      // Fallback
      if (strategies.fallback) {
        try {
          const fallback = context?.querySelector(strategies.fallback) ||
                          document.querySelector(strategies.fallback);
          if (fallback) {
            this.cache.set(cacheKey, fallback);
            return fallback;
          }
        } catch (e) {}
      }

      return null;
    }

    findAllListings() {
      const results = [];

      // Strategy 1: ARIA articles
      document.querySelectorAll('[role="article"]').forEach(el => {
        if (this.isValidListing(el)) {
          results.push(el);
        }
      });

      if (results.length === 0) {
        // Strategy 2: Structural heuristics
        document.querySelectorAll('div[role="main"] > div > div > div').forEach(el => {
          if (this.hasListingCharacteristics(el)) {
            results.push(el);
          }
        });
      }

      return results;
    }

    isValidListing(element) {
      const hasImage = element.querySelector('img') !== null;
      const hasPrice = this.extractPrice(element) !== null;
      const hasTitle = this.find(element, 'title') !== null;

      return hasImage && hasPrice && hasTitle;
    }

    hasListingCharacteristics(element) {
      // Check if element has typical listing structure
      const hasImage = element.querySelector('img') !== null;
      const hasText = element.textContent.length > 20;
      const hasLink = element.querySelector('a') !== null;

      return hasImage && hasText && hasLink;
    }

    extractPrice(element) {
      const patterns = [
        /[\$\€\£]([\d,.]+)/,
        /([\d,.]+)\s*(USD|EUR|GBP)/i
      ];

      const text = element.textContent;

      for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
          const priceStr = match[1].replace(/,/g, '');
          return parseFloat(priceStr);
        }
      }

      return null;
    }

    extractTitle(element) {
      const heading = element.querySelector('h1, h2, h3, h4, [role="heading"]');
      if (heading) {
        return heading.textContent.trim();
      }

      const spans = element.querySelectorAll('span[dir="auto"]');
      for (const span of spans) {
        const text = span.textContent.trim();
        if (text.length > 10 && text.length < 200) {
          return text;
        }
      }

      return null;
    }

    extractDescription(element) {
      // Skip the title element
      const title = this.extractTitle(element);

      // Strategy 1: Look for "Details" section - description usually comes after Condition
      const detailsHeader = element.querySelector('h2');
      if (detailsHeader) {
        // Try to find description in sibling or nearby elements
        const parent = detailsHeader.closest('div[class*="x1n2onr6"]') || detailsHeader.parentElement;
        if (parent) {
          // Look for text content after Details header
          const textElements = parent.querySelectorAll('span[dir="auto"]');
          for (const el of textElements) {
            const text = el.textContent.trim();

            // Skip if it's the title or known UI elements
            if (text === title || text === 'Details' || text === 'Condition') continue;
            if (text === 'Used - like new' || text === 'Used - good' || text === 'Used - fair' || text === 'New') continue;
            if (text.includes('Location is')) continue;
            if (text.includes('Listed ') && text.includes(' ago')) continue;

            // Skip short text, price text
            if (text.length < 10 || text.length > 500) continue;
            if (text.includes('€') || text.includes('EUR')) continue;

            // Skip UI buttons and legal text
            if (text.includes('Message Seller') || text.includes('Save') || text.includes('Share')) continue;
            if (text.includes('Learn more about purchasing') || text.includes('consumer rights')) continue;

            // Skip location patterns
            if (/^[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)?$/.test(text) && text.length < 60) continue;
            if (text.includes('Rīga') || text.includes('Latvia') || text.includes('Latvija')) continue;

            // Good candidate for description
            return text;
          }
        }
      }

      // Strategy 2: Score-based selection from all spans
      const allSpans = element.querySelectorAll('span[dir="auto"]');
      const candidates = [];

      for (const span of allSpans) {
        const text = span.textContent.trim();
        if (text === title) continue;

        let score = 0;

        // Length check
        if (text.length >= 10 && text.length <= 300) score += 10;

        // Penalize non-descriptions
        if (text === 'Details' || text === 'Condition') score -= 100;
        if (text.includes('Used -') || text === 'New') score -= 50;
        if (text.includes('Listed ') && text.includes(' ago')) score -= 100;
        if (text.includes('Location is')) score -= 100;
        if (text.includes('Learn more')) score -= 100;
        if (text.includes('Message Seller')) score -= 100;
        if (text.includes('Rīga') || text.includes('Latvia') || text.includes('Latvija')) score -= 80;
        if (text.includes('€')) score -= 50;

        // Boost for description-like content
        if (/\b(sale|sell|selling|perfect|works|condition|test)\b/i.test(text)) score += 20;

        if (score > 0) {
          candidates.push({ text, score });
        }
      }

      if (candidates.length > 0) {
        candidates.sort((a, b) => b.score - a.score);
        return candidates[0].text;
      }

      return '';
    }

    extractLocation(element) {
      // Strategy 1: Look for "Listed X ago in Location" pattern
      const allSpans = element.querySelectorAll('span[dir="auto"]');
      for (const el of allSpans) {
        const text = el.textContent.trim();
        const match = text.match(/Listed\s+[^,]+?\s+ago\s+in\s+(.+)$/);
        if (match) {
          return match[1].trim();
        }
      }
      
      // Strategy 2: Look for location links
      const locationElements = element.querySelectorAll('a[href*="/marketplace/"] span[dir="auto"]');
      for (const el of locationElements) {
        const text = el.textContent.trim();
        if (/^[A-Za-z]+(?:\s[A-Za-z]+)?,\s*[A-Za-z\s]+$/.test(text) && text.length < 60) {
          return text;
        }
      }
      
      // Strategy 3: Look for standalone location patterns
      for (const el of allSpans) {
        const text = el.textContent.trim();
        if (/^[A-Za-z]+(?:\s[A-Za-z]+)?,\s*[A-Za-z\s]+$/.test(text) && text.length < 60) {
          return text;
        }
      }
      
      return 'Unknown';
    }

    extractImage(element) {
      // Look for main product image in the listing
      const images = element.querySelectorAll('img');

      for (const img of images) {
        const src = img.src || '';

        // Must be from Facebook's CDN
        if (!src.includes('fbcdn.net')) continue;

        // Get dimensions
        const width = img.naturalWidth || img.width || 0;
        const height = img.naturalHeight || img.height || 0;

        // Skip tiny images (thumbnails)
        if (width > 0 && width < 200) continue;
        if (height > 0 && height < 200) continue;

        // Skip square thumbnails (avatars)
        if (width > 0 && height > 0 && Math.abs(width - height) < 20 && width < 150) continue;

        return src;
      }

      return '';
    }

    clearCache() {
      this.cache.clear();
    }
  }

  const selectorEngine = new SelectorEngine();

  // ==================== OVERLAY ====================

  function createOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'fb-pc-scraper-overlay';
    overlay.innerHTML = `
      <div class="scraper-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%); animation: shimmer 3s ease-in-out infinite;"></div>
        <div style="display: flex; align-items: center; gap: 10px; position: relative; z-index: 1;">
          <div style="background: rgba(255,255,255,0.2); border-radius: 8px; padding: 6px; font-size: 18px;">🔍</div>
          <div>
            <div style="font-weight: 700; font-size: 15px; letter-spacing: 0.3px;">PC Deal Analyzer</div>
            <div style="font-size: 11px; opacity: 0.8;">Live component detection</div>
          </div>
        </div>
        <button id="scraper-close" style="background: rgba(255,255,255,0.15); border: none; color: white; font-size: 20px; cursor: pointer; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; position: relative; z-index: 1;">×</button>
      </div>
      <div class="scraper-content" style="padding: 16px; max-height: 500px; overflow-y: auto; color: #333; background: linear-gradient(180deg, #fafafa 0%, #ffffff 100%);">
        <div style="text-align: center; padding: 30px 20px; color: #636e72;">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.5;">🎯</div>
          <div style="font-size: 15px; font-weight: 500; margin-bottom: 6px;">Hover over a listing</div>
          <div style="font-size: 13px; opacity: 0.7;">Click "Analyze" to detect PC components</div>
        </div>
      </div>
    `;

    // Add shimmer animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes shimmer {
        0%, 100% { transform: translateX(-100%) rotate(0deg); }
        50% { transform: translateX(100%) rotate(180deg); }
      }
    `;
    document.head.appendChild(style);

    // Container styles
    overlay.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 380px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(102,126,234,0.3), 0 4px 16px rgba(0,0,0,0.15);
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      overflow: hidden;
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    `;

    // Hover effect
    overlay.addEventListener('mouseenter', () => {
      overlay.style.transform = 'translateY(-4px)';
      overlay.style.boxShadow = '0 12px 40px rgba(102,126,234,0.4), 0 6px 20px rgba(0,0,0,0.2)';
    });

    overlay.addEventListener('mouseleave', () => {
      overlay.style.transform = 'translateY(0)';
      overlay.style.boxShadow = '0 8px 32px rgba(102,126,234,0.3), 0 4px 16px rgba(0,0,0,0.15)';
    });

    document.body.appendChild(overlay);

    // Close button hover effect
    const closeBtn = overlay.querySelector('#scraper-close');
    closeBtn.addEventListener('mouseenter', () => {
      closeBtn.style.background = 'rgba(255,255,255,0.25)';
      closeBtn.style.transform = 'scale(1.05)';
    });
    closeBtn.addEventListener('mouseleave', () => {
      closeBtn.style.background = 'rgba(255,255,255,0.15)';
      closeBtn.style.transform = 'scale(1)';
    });

    // Close button click
    closeBtn.addEventListener('click', () => {
      overlay.style.display = 'none';
    });

    return overlay;
  }

  // ==================== API CLIENT ====================

  async function analyzeListing(listingElement) {
    if (isAnalyzing) return;

    // Rate limiting
    const now = Date.now();
    if (now - requestResetTime > 60000) {
      requestCount = 0;
      requestResetTime = now;
    }

    if (requestCount >= MAX_REQUESTS_PER_MINUTE) {
      showError('Rate limit reached. Please wait a moment.');
      return;
    }

    isAnalyzing = true;
    requestCount++;

    const overlay = document.getElementById('fb-pc-scraper-overlay') || createOverlay();
    overlay.style.display = 'block';

    const content = overlay.querySelector('.scraper-content');
    content.innerHTML = `
      <div style="text-align: center; padding: 20px; color: #666;">
        <div style="width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; animation: fb-scraper-spin 1s linear infinite; margin: 0 auto 16px;"></div>
        <p style="margin: 0;">Analyzing listing...</p>
      </div>
    `;

    // Add keyframes for spinner
    if (!document.getElementById('scraper-styles')) {
      const style = document.createElement('style');
      style.id = 'scraper-styles';
      style.textContent = `
        @keyframes fb-scraper-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }

    // Extract listing data - try multiple methods
    let title, description, price, seller_location, image_url;

    if (listingElement) {
      // We have a specific listing element (from hover)
      title = selectorEngine.extractTitle(listingElement) || '';
      description = selectorEngine.extractDescription(listingElement) || '';
      price = selectorEngine.extractPrice(listingElement) || 0;
      seller_location = selectorEngine.extractLocation(listingElement) || 'Unknown';
      image_url = selectorEngine.extractImage(listingElement) || '';
    } else {
      // Single listing page - extract from whole page
      title = extractPageTitle();
      description = extractPageDescription();
      price = extractPagePrice();
      seller_location = extractPageLocation();
      image_url = extractPageImage();
    }

    // DEBUG: Log what was extracted
    console.log('[FB Scraper] Extracted description raw:', description);
    console.log('[FB Scraper] Description length:', description?.length);
    console.log('[FB Scraper] Contains "Public meetup":', description?.toLowerCase().includes('public meetup'));
    console.log('[FB Scraper] Contains Cyrillic:', /[\u0400-\u04FF]/.test(description || ''));
    console.log('[FB Scraper] Extracted image:', image_url ? image_url.substring(0, 80) : 'none');

    console.log('[FB Scraper] Extracted:', { title, price, seller_location, descriptionLength: description?.length, hasImage: !!image_url });

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title,
          description,
          price,
          currency: 'EUR',
          image_url
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[FB Scraper] Server error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success) {
        showResults(data, content, title, description, seller_location, image_url);
      } else {
        throw new Error(data.error || 'Analysis failed');
      }

    } catch (error) {
      console.error('[FB Scraper] Analysis failed:', error);
      showError('Failed to analyze listing. Check if the backend is running.', content);
    } finally {
      isAnalyzing = false;
    }
  }

  function showResults(data, content, listingTitle, listingDescription, sellerLocation, imageUrl) {
    const { components, pricing } = data;

    let totalValue = 0;
    let componentsHtml = '';

    const componentIcons = {
      cpu: '🧠', gpu: '🎮', ram: '💾',
      ssd: '💿', psu: '⚡', case: '📦',
      motherboard: '📟', monitor: '🖥️'
    };

    const componentColors = {
      cpu: '#667eea', gpu: '#f093fb', ram: '#4facfe',
      ssd: '#43e97b', psu: '#fa709a', case: '#fee140',
      motherboard: '#30cfd0', monitor: '#a8edea'
    };

    const dealLabels = {
      excellent: { emoji: '🤩', label: 'Excellent Deal', color: '#00b894', bg: '#d4edda' },
      good: { emoji: '🔥', label: 'Good Deal', color: '#00b894', bg: '#d4edda' },
      fair: { emoji: '👍', label: 'Fair Price', color: '#fdcb6e', bg: '#fff3cd' },
      high: { emoji: '⚠️', label: 'Above Market', color: '#e17055', bg: '#ffe0b2' },
      overpriced: { emoji: '❌', label: 'Overpriced', color: '#d63031', bg: '#f8d7da' },
      unknown: { emoji: '❓', label: 'Unknown', color: '#636e72', bg: '#e2e3e5' }
    };

    for (const [type, component] of Object.entries(components)) {
      totalValue += component.prices?.avg || 0;

      const icon = componentIcons[type] || '🔧';
      const color = componentColors[type] || '#667eea';
      const confidence = Math.round((component.confidence || 0) * 100);

      componentsHtml += `
        <div style="background: linear-gradient(135deg, ${color}15 0%, ${color}08 100%); border-left: 4px solid ${color}; border-radius: 8px; padding: 12px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-weight: 700; color: ${color}; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
              ${icon} ${type.toUpperCase()}
            </span>
            <span style="background: ${color}; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">
              ${confidence}% match
            </span>
          </div>
          <div style="font-size: 16px; font-weight: 600; color: #2d3436; margin-bottom: 4px; line-height: 1.3;">
            ${component.detected || 'N/A'}
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
            <span style="color: #636e72;">${component.normalized || ''}</span>
            <span style="color: #27ae60; font-weight: 700; font-size: 15px;">€${component.prices?.avg || 'N/A'}</span>
          </div>
        </div>
      `;
    }

    const deal = dealLabels[pricing.deal_rating] || dealLabels.unknown;
    const savings = (pricing.estimated_total || 0) - (pricing.listed_price || 0);
    const savingsText = savings > 0 ? `Save €${savings.toFixed(0)}!` : savings < 0 ? `Overpaying €${Math.abs(savings).toFixed(0)}` : '';

    // Generate unique ID for this listing
    const listingId = `fb_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Store current analysis data for import
    // Extract URL and image from the page
    const listingUrl = window.location.href;

    // Use the same image extraction as analyzeListing (imageUrl is passed as parameter)
    const finalImageUrl = imageUrl || data.image_url || extractPageImage();

    // Determine category based on matched components
    let category = 'computer';
    if (components.gpu && !components.cpu) category = 'gpu';
    else if (components.cpu && !components.gpu) category = 'cpu';

    window.currentAnalysisData = {
      listingId,
      title: listingTitle || 'Unknown',
      description: listingDescription || '',
      price: pricing.listed_price,
      currency: 'EUR',
      listing_url: listingUrl,
      image_url: finalImageUrl,
      seller_location: sellerLocation || 'Unknown',
      components,
      pricing,
      category
    };

    // Check if GPU was detected but not matched to a known model
    let unmatchedWarning = '';
    if (components.gpu && !components.gpu.matched_model?.id) {
      unmatchedWarning = `
        <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 12px; margin-bottom: 16px; color: #856404;">
          <div style="font-weight: 600; margin-bottom: 4px;">⚠️ GPU Not Matched to Database</div>
          <div style="font-size: 13px;">This GPU model may not be in our database. The listing will be saved but won't have price comparison data.</div>
        </div>
      `;
    }

    content.innerHTML = `
      <div style="padding: 4px;">
        <div style="margin-bottom: 16px;">
          ${unmatchedWarning}
          ${componentsHtml || '<div style="text-align: center; padding: 20px; color: #636e72;">No PC components detected in this listing</div>'}
        </div>

        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 16px; color: white; box-shadow: 0 4px 15px rgba(102,126,234,0.4);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
              <div style="font-size: 12px; opacity: 0.9; margin-bottom: 2px;">Component Value</div>
              <div style="font-size: 24px; font-weight: 700;">€${pricing.estimated_total || 0}</div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 12px; opacity: 0.9; margin-bottom: 2px;">Listed Price</div>
              <div style="font-size: 24px; font-weight: 700; ${pricing.listed_price < pricing.estimated_total ? 'color: #55efc4;' : 'color: #fab1a0;'}">€${pricing.listed_price || 0}</div>
            </div>
          </div>

          ${savingsText ? `<div style="text-align: center; font-size: 14px; font-weight: 600; margin-bottom: 12px; padding: 8px; background: rgba(255,255,255,0.2); border-radius: 6px;">${savingsText}</div>` : ''}

          <div style="display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px; background: ${deal.bg}; border-radius: 8px; color: ${deal.color}; font-weight: 700; font-size: 16px; margin-bottom: 12px;">
            <span style="font-size: 20px;">${deal.emoji}</span>
            <span>${deal.label}</span>
          </div>

          <div style="display: flex; gap: 8px; margin-bottom: 12px;">
            <button id="clear-btn-${listingId}" style="flex: 1; background: linear-gradient(135deg, #636e72 0%, #b2bec3 100%); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
              <span style="font-size: 18px;">🔄</span>
              <span>Clear / New Scrape</span>
            </button>
            <button id="import-btn-${listingId}" style="flex: 1; background: linear-gradient(135deg, #00b894 0%, #00cec9 100%); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
              <span style="font-size: 18px;">💾</span>
              <span>Import to Database</span>
            </button>
          </div>
        </div>
      </div>
    `;

    // Add import button click handler
    const importBtn = document.getElementById(`import-btn-${listingId}`);
    if (importBtn) {
      importBtn.addEventListener('click', () => importListing(window.currentAnalysisData, importBtn));
    }

    // Add clear button click handler
    const clearBtn = document.getElementById(`clear-btn-${listingId}`);
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        // Reset the overlay for a new scrape
        const content = document.querySelector('.scraper-content');
        if (content) {
          content.innerHTML = `
            <div style="text-align: center; padding: 20px;">
              <div style="font-size: 48px; margin-bottom: 12px;">🔍</div>
              <p style="color: #636e72; margin-bottom: 16px; font-size: 14px;">Click "Analyze This Listing" to scan for PC components</p>
              <button id="reanalyze-btn" style="background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600;">Analyze This Listing</button>
            </div>
          `;
          // Re-bind the analyze button
          const reanalyzeBtn = document.getElementById('reanalyze-btn');
          if (reanalyzeBtn) {
            reanalyzeBtn.addEventListener('click', () => {
              // Run analysis for single page (no element needed)
              analyzeListing(null, content);
            });
          }
        }
      });
    }
  }

  async function importListing(data, btnElement) {
    btnElement.disabled = true;
    btnElement.innerHTML = '<span style="font-size: 18px;">⏳</span><span>Importing...</span>';

    try {
      // Use background script to avoid CORS issues with localhost
      const result = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
          action: 'import',
          data: {
            title: data.title,
            description: data.description,
            price: data.price,
            currency: data.currency,
            listing_url: data.listing_url,
            image_url: data.image_url,
            seller_location: data.seller_location,
            category: data.category,
            components: data.components,
            pricing: data.pricing
          }
        }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.error || 'Import failed'));
          }
        });
      });

      btnElement.style.background = 'linear-gradient(135deg, #00b894 0%, #55efc4 100%)';
      btnElement.innerHTML = '<span style="font-size: 18px;">✅</span><span>Imported!</span>';
      setTimeout(() => {
        btnElement.disabled = false;
        btnElement.innerHTML = '<span style="font-size: 18px;">💾</span><span>Import to Database</span>';
      }, 3000);
    } catch (error) {
      console.error('[FB Scraper] Import failed:', error);
      btnElement.style.background = 'linear-gradient(135deg, #e74c3c 0%, #fab1a0 100%)';
      btnElement.innerHTML = '<span style="font-size: 18px;">❌</span><span>Failed</span>';
      btnElement.disabled = false;
    }
  }

  function showError(message, content) {
    content.innerHTML = `
      <div style="text-align: center; padding: 20px;">
        <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
        <p style="color: #e74c3c; margin-bottom: 16px; font-size: 14px;">${message}</p>
        <button style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: background 0.2s;" onclick="location.reload()">Retry</button>
      </div>
    `;
  }

  // ==================== INITIALIZATION ====================

  function init() {
    console.log('[FB Scraper] Extension loaded');

    // Create overlay
    createOverlay();

    // Setup mutation observer
    setupMutationObserver();

    // Initial scan
    enhanceExistingListings();
  }

  function setupMutationObserver() {
    observer = new MutationObserver((mutations) => {
      // Debounce mutations
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }

      debounceTimer = setTimeout(() => {
        handleMutations(mutations);
      }, DEBOUNCE_MS);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  function handleMutations(mutations) {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === 1) {
          // Check if node or its children are listings
          if (selectorEngine.isValidListing(node)) {
            enhanceListing(node);
          }

          node.querySelectorAll?.('[role="article"]').forEach(el => {
            if (selectorEngine.isValidListing(el)) {
              enhanceListing(el);
            }
          });
        }
      }
    }
  }

  function enhanceExistingListings() {
    const listings = selectorEngine.findAllListings();
    listings.forEach(enhanceListing);
  }

  function enhanceListing(listingElement) {
    // Skip if already enhanced
    if (listingElement.dataset.pcScraperEnhanced) return;
    listingElement.dataset.pcScraperEnhanced = 'true';

    // Add analyze button
    const analyzeBtn = document.createElement('button');
    analyzeBtn.className = 'scraper-analyze-btn';
    analyzeBtn.textContent = '🔍 Analyze';
    analyzeBtn.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: #667eea;
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      z-index: 100;
      opacity: 0;
      transition: opacity 0.2s;
    `;

    analyzeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      analyzeListing(listingElement);
    });

    listingElement.style.position = 'relative';
    listingElement.appendChild(analyzeBtn);

    // Show on hover
    listingElement.addEventListener('mouseenter', () => {
      analyzeBtn.style.opacity = '1';
    });

    listingElement.addEventListener('mouseleave', () => {
      analyzeBtn.style.opacity = '0';
    });
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'scrapePage') {
      (async () => {
        try {
          // Check if we're on Facebook (broader check)
          const url = window.location.href;
          if (!url.includes('facebook.com')) {
            sendResponse({ success: false, error: 'Not on Facebook' });
            return;
          }

          console.log('[FB Scraper] Manual scrape triggered on:', url);

          // Trigger analysis
          await analyzeListing(null);
          sendResponse({ success: true });
        } catch (error) {
          console.error('[FB Scraper] Manual scrape error:', error);
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true; // Keep channel open for async
    }
  });

  // Start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ==================== SINGLE PAGE EXTRACTION HELPERS ====================

  function extractPageTitle() {
    // Strategy 1: Find h1 that contains GPU/CPU/PC hardware keywords
    const h1s = document.querySelectorAll('h1');
    for (const h1 of h1s) {
      const text = h1.textContent.trim();

      // Skip UI elements like "Notifications", "Menu", etc
      const uiTerms = ['Notifications', 'Menu', 'Search', 'Messages', 'Save', 'Share', 'Message Seller', 'Details'];
      if (uiTerms.some(term => text.toLowerCase().includes(term.toLowerCase()))) {
        continue;
      }

      // Check if it contains product-related terms
      const productTerms = ['GeForce', 'Radeon', 'GTX', 'RTX', 'RX', 'Intel', 'AMD', 'Core', 'Ryzen', 'PC', 'Computer', 'Monitor', 'Laptop'];
      if (productTerms.some(term => text.toLowerCase().includes(term.toLowerCase()))) {
        return text;
      }

      // If it has a reasonable length (not too short, not too long)
      if (text.length > 10 && text.length < 150) {
        return text;
      }
    }

    // Strategy 2: Find span inside h1 with specific pattern
    const h1Span = document.querySelector('h1 span[dir="auto"]');
    if (h1Span) {
      const text = h1Span.textContent.trim();
      const uiTerms = ['Notifications', 'Menu', 'Search', 'Messages', 'Save', 'Share'];
      if (!uiTerms.some(term => text.toLowerCase().includes(term.toLowerCase()))) {
        if (text.length > 10 && text.length < 150) {
          return text;
        }
      }
    }

    // Strategy 3: Look for title with price nearby
    const titleSection = document.querySelector('div[class*="x1xmf6yo"]');
    if (titleSection) {
      const span = titleSection.querySelector('span[dir="auto"]');
      if (span) {
        const text = span.textContent.trim();
        if (text.length > 10 && text.length < 150) {
          const uiTerms = ['Notifications', 'Menu', 'Search', 'Messages'];
          if (!uiTerms.some(term => text.toLowerCase().includes(term.toLowerCase()))) {
            return text;
          }
        }
      }
    }

    // Strategy 4: Any span with product keywords and reasonable length
    const spans = document.querySelectorAll('span[dir="auto"]');
    for (const span of spans) {
      const text = span.textContent.trim();
      const productTerms = ['GeForce', 'Radeon', 'GTX', 'RTX', 'RX', 'Intel', 'AMD', 'Core', 'Ryzen'];
      if (productTerms.some(term => text.toLowerCase().includes(term.toLowerCase()))) {
        if (text.length > 10 && text.length < 150) {
          return text;
        }
      }
    }

    return '';
  }

  function extractPageDescription() {
    // Strategy: Look for text in the Details section - it's usually after "Condition" row
    // The real description is in a span[dir="auto"] within the Details container

    // Find the Details section by looking for the "Details" h2
    const detailsHeaders = document.querySelectorAll('h2');
    let detailsContainer = null;

    for (const h2 of detailsHeaders) {
      if (h2.textContent.includes('Details')) {
        // The description is usually in a sibling or nearby container
        detailsContainer = h2.closest('div[class*="x1n2onr6"]') || h2.parentElement?.parentElement;
        break;
      }
    }

    if (detailsContainer) {
      // Look for spans with product description text within the Details container
      const spans = detailsContainer.querySelectorAll('span[dir="auto"]');
      for (const span of spans) {
        const text = span.textContent.trim();

        // Must have Cyrillic OR product keywords
        const hasCyrillic = /[\u0400-\u04FF]/.test(text);
        const hasProductKeywords = /\b(ryzen|intel|core|i[3579]|geforce|rtx|gtx|cpu|gpu|ram|pc|computer|amd)\b/i.test(text);

        if (!hasCyrillic && !hasProductKeywords) continue;

        // Must be reasonable length
        if (text.length < 20) continue;

        // Skip UI buttons
        if (span.closest('button, [role="button"]')) continue;

        // Skip if parent has icon
        let hasIconParent = false;
        let parent = span.parentElement;
        for (let i = 0; i < 3 && parent; i++) {
          if (parent.querySelector && parent.querySelector('i[data-visualcompletion="css-img"]')) {
            hasIconParent = true;
            break;
          }
          parent = parent.parentElement;
        }
        if (hasIconParent) continue;

        // Skip location text
        if (text.includes('Rīga') || text.includes('Latvia') || text.includes('Latvija')) continue;

        // Skip generic UI text
        if (text.toLowerCase().includes('public meetup')) continue;

        console.log('[FB Scraper] Found description in Details section:', text.substring(0, 60));
        return text;
      }
    }

    // Fallback: Search all spans for product description text
    // Accept Cyrillic OR Latin-based languages with product keywords
    const allSpans = document.querySelectorAll('span[dir="auto"]');

    for (const span of allSpans) {
      const text = span.textContent.trim();

      // Must be reasonable length
      if (text.length < 20) continue;

      // Must contain either Cyrillic OR be a product description (has product keywords)
      const hasCyrillic = /[\u0400-\u04FF]/.test(text);
      const hasProductKeywords = /\b(ryzen|intel|core|i[3579]|geforce|rtx|gtx|cpu|gpu|ram|pc|computer|amd)\b/i.test(text);

      if (!hasCyrillic && !hasProductKeywords) continue;

      // Must not be in a button
      if (span.closest('button, [role="button"]')) continue;

      // Must not have icon in parent
      let hasIconParent = false;
      let parent = span.parentElement;
      for (let i = 0; i < 5 && parent; i++) {
        if (parent.querySelector && parent.querySelector('i[data-visualcompletion="css-img"]')) {
          hasIconParent = true;
          break;
        }
        parent = parent.parentElement;
      }
      if (hasIconParent) continue;

      // Skip location text
      if (text.includes('Rīga') || text.includes('Latvia') || text.includes('Latvija')) continue;

      // Skip generic UI text
      if (text.toLowerCase().includes('public meetup')) continue;

      console.log('[FB Scraper] Found description:', text.substring(0, 60));
      return text;
    }

    console.log('[FB Scraper] No suitable description found');
    return '';
  }

  function extractPagePrice() {
    // Look for currency symbols
    const text = document.body.innerText;
    const patterns = [
      /[\$\€\£]([\d,.]+)/,
      /([\d,.]+)\s*(EUR|USD|GBP)/i
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        const priceStr = match[1].replace(/,/g, '');
        return parseFloat(priceStr);
      }
    }

    return 0;
  }

  function extractPageLocation() {
    // Strategy 1: Look for "Listed X ago in Location" pattern - this is the primary location
    const allSpans = document.querySelectorAll('span[dir="auto"]');
    for (const span of allSpans) {
      const text = span.textContent.trim();
      // Match: "Listed 4 weeks ago in Rīga, Latvija"
      const match = text.match(/Listed\s+[^,]+?\s+ago\s+in\s+(.+)$/);
      if (match) {
        return match[1].trim();
      }
    }

    // Strategy 2: Look for location in the link to marketplace location
    const locationLink = document.querySelector('a[href*="/marketplace/"]');
    if (locationLink) {
      const span = locationLink.querySelector('span[dir="auto"]');
      if (span) {
        const text = span.textContent.trim();
        // Only return if it looks like a location (not "Learn more" etc)
        if (text.length < 60 && text.includes(',')) {
          return text;
        }
      }
    }

    // Strategy 3: Look for standalone location text (after "Location is approximate")
    for (const span of allSpans) {
      const text = span.textContent.trim();
      // Location patterns like "Rīga, Latvija"
      if (/^[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)?$/.test(text) &&
          text.length < 60 && text.includes(',')) {
        return text;
      }
    }

    // Strategy 4: Look for nearby spans to "Location is approximate"
    const locationApproxText = Array.from(allSpans).find(span =>
      span.textContent.includes('Location is approximate')
    );
    if (locationApproxText) {
      // Look at the container and nearby elements
      const container = locationApproxText.closest('div[class*="x14vqqas"]') ||
                       locationApproxText.parentElement;
      if (container) {
        const nearby = container.querySelectorAll('span[dir="auto"]');
        for (const span of nearby) {
          if (span !== locationApproxText) {
            const text = span.textContent.trim();
            if (text.length < 60 && (text.includes(',') || /Rīga|Latvia|Latvija/.test(text))) {
              return text;
            }
          }
        }
      }
    }

    return 'Unknown';
  }

  function extractPageImage() {
    // Strategy 1: Look for the main product image in the gallery container
    // The main image is typically in a container with specific Facebook classes
    // and has a large size (not a thumbnail)

    // Find images that are product photos (not thumbnails, not icons)
    const allImages = document.querySelectorAll('img');

    for (const img of allImages) {
      const src = img.src || '';

      // Must be from Facebook's CDN
      if (!src.includes('fbcdn.net')) continue;

      // Skip tiny images (likely thumbnails, icons, or avatars)
      // Get natural dimensions if available, otherwise use element dimensions
      const width = img.naturalWidth || img.width || 0;
      const height = img.naturalHeight || img.height || 0;

      if (width > 0 && width < 300) continue; // Too small to be main image
      if (height > 0 && height < 300) continue;

      // Skip profile pictures (square avatars)
      if (width > 0 && height > 0 && Math.abs(width - height) < 20 && width < 100) continue;

      // Check if it's in a product photo container
      const parent = img.parentElement;
      if (parent) {
        const parentClasses = parent.className || '';
        // Product photo containers have specific classes
        if (parentClasses.includes('x1ey2m1c') ||
            parentClasses.includes('x5yr21d') ||
            parentClasses.includes('xti2d7y')) {
          console.log('[FB Scraper] Found main image:', src.substring(0, 80));
          return src;
        }
      }

      // Look for images with alt text containing product keywords
      const alt = img.alt || '';
      if (alt.toLowerCase().includes('product photo')) {
        console.log('[FB Scraper] Found image with product alt:', src.substring(0, 80));
        return src;
      }
    }

    // Strategy 2: Look for images in the main content area
    // Find the largest image from Facebook CDN
    let bestImage = null;
    let bestSize = 0;

    for (const img of allImages) {
      const src = img.src || '';
      if (!src.includes('fbcdn.net')) continue;

      const width = img.naturalWidth || img.width || 0;
      const height = img.naturalHeight || img.height || 0;
      const size = width * height;

      // Skip if smaller than current best
      if (size <= bestSize) continue;

      // Skip tiny images
      if (width < 400 || height < 400) continue;

      // Skip square thumbnails
      if (Math.abs(width - height) < 50 && width < 200) continue;

      bestImage = src;
      bestSize = size;
    }

    if (bestImage) {
      console.log('[FB Scraper] Found best image by size:', bestImage.substring(0, 80));
      return bestImage;
    }

    console.log('[FB Scraper] No suitable image found');
    return '';
  }

  // Helper function to get element depth in DOM
  function getElementDepth(element) {
    let depth = 0;
    let node = element;
    while (node && node !== document.body) {
      depth++;
      node = node.parentElement;
    }
    return depth;
  }
})();
