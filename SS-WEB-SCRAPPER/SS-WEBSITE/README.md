# SS-Crawler Web Dashboard

A web interface for viewing scraped GPU and CPU data from ss.com marketplace.

## Features

- **Dashboard Overview**: Statistics and price trends
- **GPU Listings**: View all GPU listings with price comparisons
- **CPU Listings**: View all CPU listings with price comparisons  
- **Model Statistics**: Aggregated stats by GPU/CPU model
- **Price Indicators**:
  - 🔴 Below average (good deal)
  - 🟢 Above average (premium)
  - Price percentile bar showing where each listing sits in the market

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Make sure the database is running
# Then start the web server
python app.py
```

The dashboard will be available at: http://localhost:5000

## Pages

- `/` - Dashboard with overview stats and charts
- `/gpu` - GPU listings table with filters
- `/cpu` - CPU listings table with filters
- `/models` - Model statistics cards

## API Endpoints

- `GET /api/stats` - Overall statistics
- `GET /api/gpus` - GPU listings (query: `active`, `min_confidence`)
- `GET /api/cpus` - CPU listings (query: `active`, `min_confidence`)
- `GET /api/gpu-models` - Aggregated GPU model statistics
- `GET /api/cpu-models` - Aggregated CPU model statistics
- `GET /api/price-history/<listing_id>` - Price history for a listing
