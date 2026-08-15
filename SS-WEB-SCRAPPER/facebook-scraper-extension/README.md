# Facebook Marketplace PC Scraper - Chrome Extension

## Phase 1: Foundation - Implementation Complete

### Overview
A Chrome browser extension that scrapes Facebook Marketplace listings, detects PC components, and displays live pricing analytics.

### Project Structure
```
facebook-scraper-extension/
├── manifest.json          # Extension configuration (v3)
├── background.js          # Service worker for API calls
├── content.js             # Main scraper logic
├── popup.html             # Extension popup UI
├── styles.css             # Overlay styling
├── schema.sql             # Database schema
├── icons/
│   └── icon.svg           # Extension icon
└── README.md
```

### Features Implemented

#### Backend (Flask API)
- ✅ `/api/v1/extension/analyze` - POST endpoint for component detection
- ✅ `/api/v1/extension/health` - Health check endpoint
- ✅ Component detection (GPU, CPU, RAM, SSD)
- ✅ Price normalization to EUR
- ✅ Deal rating calculation
- ✅ Basic confidence scoring

#### Database Schema
- ✅ Component reference tables (gpu_details, cpu_details, ram_details, ssd_details)
- ✅ Price history tracking
- ✅ Detection cache with versioning
- ✅ Privacy-preserving telemetry
- ✅ Sample data for testing

#### Extension (Chrome)
- ✅ Manifest v3 configuration
- ✅ Selector abstraction layer
- ✅ Multi-layer DOM detection strategies
- ✅ Debounced mutation observer
- ✅ Rate limiting (60 req/min)
- ✅ In-memory caching
- ✅ Draggable overlay UI
- ✅ Error handling with retry
- ✅ Dark mode support

### Installation

#### 1. Database Setup
```bash
cd SS-WEBSITE
psql -U your_user -d your_database -f ../facebook-scraper-extension/schema.sql
```

#### 2. Extension Installation
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `facebook-scraper-extension` folder

#### 3. Backend Configuration
Ensure the Flask backend is running:
```bash
cd SS-WEBSITE
python app.py
```

### Usage

1. Navigate to Facebook Marketplace
2. Hover over PC listings to see "Analyze" button
3. Click "Analyze" to see:
   - Detected components (CPU, GPU, RAM, SSD)
   - Estimated values
   - Deal rating (Excellent/Good/Fair/Overpriced)
   - Confidence scores

### API Documentation

#### POST /api/v1/extension/analyze
Analyze a listing for PC components.

**Request:**
```json
{
  "title": "Gaming PC i7-12700K RTX 3080",
  "description": "32GB DDR4, 1TB NVMe",
  "price": 1200,
  "currency": "EUR"
}
```

**Response:**
```json
{
  "success": true,
  "components": {
    "gpu": {
      "detected": "RTX 3080",
      "normalized": "nvidia geforce rtx3080",
      "confidence": 0.85,
      "prices": {
        "avg": 650,
        "min": 500,
        "max": 800,
        "currency": "EUR"
      }
    }
  },
  "pricing": {
    "estimated_total": 1400,
    "listed_price": 1200,
    "deal_rating": "good"
  }
}
```

### Architecture

```
Facebook Marketplace Page
        │
        ▼
┌─────────────────────────────┐
│  Content Script (content.js)│
│  - Selector Engine          │
│  - Mutation Observer        │
│  - Overlay UI               │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Background (background.js)│
│  - Rate limiting           │
│  - Caching                │
│  - API client             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Flask API (app.py)        │
│  - Component detection     │
│  - Price lookup            │
│  - Deal rating             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  PostgreSQL Database         │
│  - Component reference       │
│  - Price history             │
│  - Detection cache           │
└─────────────────────────────┘
```

### Phase 1 Complete ✅

- [x] Extension manifest
- [x] Database schema
- [x] API endpoints
- [x] Content script with selector engine
- [x] Background service worker
- [x] Overlay UI
- [x] Rate limiting
- [x] Basic caching

### Phase 2 TODO

- [ ] Advanced ambiguity resolution
- [ ] Evidence vs certainty separation
- [ ] Multi-language support
- [ ] Price history integration
- [ ] Telemetry dashboard
- [ ] Staged rollout

### Configuration

Environment variables for backend:
```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=ss_market
DATABASE_USER=crawler
DATABASE_PASSWORD=your_password
```

### Troubleshooting

**Extension not loading:**
- Check `chrome://extensions/` for errors
- Verify manifest.json is valid JSON

**Backend connection failed:**
- Ensure Flask server is running on port 5000
- Check CORS configuration in app.py
- Verify database connection

**No listings detected:**
- Facebook may have changed DOM structure
- Check browser console for errors
- Selector engine may need updating

### Development

Run Flask backend with auto-reload:
```bash
flask run --reload
```

View extension console logs:
1. Go to `chrome://extensions/`
2. Find the extension
3. Click "background page" (for service worker logs)
4. Or right-click extension icon → "Inspect popup"

### License

MIT License - See LICENSE file

### Author

OpenClaw Agent - 2026
