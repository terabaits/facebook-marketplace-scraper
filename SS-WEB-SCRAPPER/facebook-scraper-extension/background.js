/**
 * Facebook Marketplace PC Scraper - Background Service Worker
 * Phase 1: Foundation
 */

// API Configuration
const API_URL = 'http://localhost:5001/api/v1/extension';

// Rate limiting state
let requestCount = 0;
let requestResetTime = Date.now();
const MAX_REQUESTS_PER_MINUTE = 60;

// Cache for API responses
const apiCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// Message handlers
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'analyze') {
    handleAnalyzeRequest(request.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Async response
  }
  
  if (request.action === 'import') {
    handleImportRequest(request.data)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Async response
  }
  
  if (request.action === 'logError') {
    logTelemetry('error', request.error);
    sendResponse({ success: true });
    return false;
  }
  
  if (request.action === 'getCache') {
    const cached = getCachedResult(request.key);
    sendResponse({ cached });
    return false;
  }
  
  if (request.action === 'setCache') {
    setCachedResult(request.key, request.data);
    sendResponse({ success: true });
    return false;
  }
});

// Installation handler
chrome.runtime.onInstalled.addListener(() => {
  console.log('[FB Scraper] Extension installed');
  logTelemetry('extension_installed', { version: '1.0.0' });
});

/**
 * Handle analyze request with rate limiting
 */
async function handleAnalyzeRequest(data) {
  // Check rate limit
  const now = Date.now();
  if (now - requestResetTime > 60000) {
    requestCount = 0;
    requestResetTime = now;
  }
  
  if (requestCount >= MAX_REQUESTS_PER_MINUTE) {
    throw new Error('Rate limit exceeded');
  }
  
  requestCount++;
  
  // Check cache
  const cacheKey = generateCacheKey(data);
  const cached = getCachedResult(cacheKey);
  if (cached) {
    logTelemetry('cache_hit', { cacheKey });
    return { ...cached, cacheHit: true };
  }
  
  // Make API request
  const startTime = Date.now();
  
  try {
    const response = await fetch('http://localhost:5001/api/v1/extension/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    
    const processingTime = Date.now() - startTime;
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      logTelemetry('api_error', { 
        status: response.status, 
        error: error.error,
        processingTime 
      });
      throw new Error(error.error || `API error: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Cache successful result
    if (result.success) {
      setCachedResult(cacheKey, result);
    }
    
    logTelemetry('api_success', { 
      processingTime,
      componentsDetected: Object.keys(result.components || {}).length
    });
    
    return result;
    
  } catch (error) {
    logTelemetry('api_exception', { 
      error: error.message,
      processingTime: Date.now() - startTime
    });
    throw error;
  }
}

/**
 * Handle import request
 */
async function handleImportRequest(data) {
  const response = await fetch(`${API_URL}/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}


/**
 * Generate cache key from request data
 */
function generateCacheKey(data) {
  // Simple hash of title + price
  const str = `${data.title}:${data.price}`;
  return hashString(str);
}

/**
 * Simple string hash
 */
function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(16);
}

/**
 * Get cached result
 */
function getCachedResult(key) {
  const cached = apiCache.get(key);
  if (!cached) return null;
  
  if (Date.now() - cached.timestamp > CACHE_TTL) {
    apiCache.delete(key);
    return null;
  }
  
  return cached.data;
}

/**
 * Set cached result
 */
function setCachedResult(key, data) {
  apiCache.set(key, {
    data,
    timestamp: Date.now()
  });
  
  // Clean old cache entries
  cleanOldCache();
}

/**
 * Clean old cache entries
 */
function cleanOldCache() {
  const now = Date.now();
  for (const [key, value] of apiCache) {
    if (now - value.timestamp > CACHE_TTL) {
      apiCache.delete(key);
    }
  }
}

/**
 * Log telemetry event
 */
function logTelemetry(eventType, data) {
  const event = {
    eventType,
    timestamp: new Date().toISOString(),
    extensionVersion: '1.0.0',
    ...data
  };
  
  // In production, send to backend
  console.log('[Telemetry]', event);
}

// Periodic cleanup
setInterval(cleanOldCache, CACHE_TTL);
