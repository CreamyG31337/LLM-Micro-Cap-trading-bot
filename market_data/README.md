# Market Data Module

The market data module handles fetching, caching, and managing market data from multiple sources with robust fallback mechanisms. It provides market timing utilities and price data management.

## Structure

```
market_data/
├── data_fetcher.py    # Multi-source data fetching with fallbacks
├── market_hours.py    # Market timing and trading day logic
├── price_cache.py     # Price caching and performance optimization
└── README.md         # This file
```

## Data Fetcher (`data_fetcher.py`)

Implements a robust multi-stage fallback strategy for fetching OHLCV data:

### Fallback Strategy
1. **Yahoo Finance** (via yfinance) - Primary source
2. **Stooq** (via pandas-datareader) - First fallback
3. **Stooq Direct CSV** - Second fallback
4. **Index Proxies** - Final fallback (e.g., ^GSPC→SPY, ^RUT→IWM)

### Key Features
- **Automatic Fallbacks**: Seamlessly switches between data sources
- **Symbol Mapping**: Handles different symbol formats across sources
- **Error Recovery**: Graceful handling of network and API failures
- **Proxy Support**: Uses ETF proxies for unavailable index data

### Usage Example
```python
from market_data.data_fetcher import MarketDataFetcher
from datetime import datetime, timedelta

fetcher = MarketDataFetcher()

# Fetch recent price data
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

data = fetcher.fetch_price_data(["AAPL", "GOOGL"], start_date, end_date)
```

### Supported Data Sources
- **Yahoo Finance**: Primary source for most stocks and ETFs
- **Stooq**: European markets and some indices
- **Index Proxies**: ETF alternatives for major indices

## Market Hours (`market_hours.py`)

Provides market timing and trading day calculations:

### Key Functions
- `is_market_open()`: Check if markets are currently open
- `is_trading_day(date)`: Check if a specific date is a trading day
- `last_trading_date()`: Get the most recent trading day
- `trading_day_window()`: Calculate trading day ranges
- `get_market_timezone()`: Get appropriate timezone for markets

### Important: When to Use `is_market_open()`

**✅ Correct Usage:**
- **Timestamp decisions**: Use 16:00 if closed, current time if open
- **Check existing data**: See if we already have market close snapshot
- **Avoid overwriting**: Don't replace market close with intraday data

**❌ Incorrect Usage:**
- **Skip creation**: Don't skip creating snapshots just because market is closed
- **Skip fetching**: Don't skip fetching data just because market is closed
- **Skip updates**: Don't skip updates just because market is closed

**Example:**
```python
# ❌ WRONG - Don't skip just because market is closed
if market_hours.is_trading_day(today) and market_hours.is_market_open():
    create_snapshot()

# ✅ CORRECT - Create if trading day, use market close time if closed
if market_hours.is_trading_day(today):
    timestamp = datetime.now() if market_hours.is_market_open() else market_close_time
    create_snapshot(timestamp)
```

### Market Support
- **North American Markets**: NYSE, NASDAQ (Eastern Time)
- **Canadian Markets**: TSX, TSX-V (Eastern Time)
- **Holiday Handling**: Accounts for market holidays
- **Weekend Logic**: Proper weekend handling

### Usage Example
```python
from market_data.market_hours import is_market_open, last_trading_date

# Check if market is open
if is_market_open():
    print("Market is open for trading")

# Get last trading day
last_day = last_trading_date()
```

## Price Cache (`price_cache.py`)

Implements in-memory price caching for performance optimization:

### Features
- **In-Memory Caching**: Fast access to recently fetched prices
- **Cache Invalidation**: Automatic expiration of stale data
- **Persistence Strategy**: Optional disk persistence for cache
- **Memory Management**: Automatic cleanup of old cache entries

### Cache Strategies
- **Time-based Expiration**: Cache expires after configurable time
- **Market Hours Aware**: Different expiration during/after market hours
- **Selective Caching**: Cache only frequently accessed symbols

### Usage Example
```python
from market_data.price_cache import PriceCache

cache = PriceCache()

# Check cache first
cached_price = cache.get_cached_price("AAPL", datetime.now().date())

if cached_price is None:
    # Fetch and cache new data
    price = fetcher.fetch_current_price("AAPL")
    cache.cache_price("AAPL", price, datetime.now().date())
```

## Integration with Repository Pattern

The market data module is designed to work with both current CSV storage and future database backends:

### Current CSV Integration
- Fetched data is stored in CSV format
- Compatible with existing file structures
- Maintains historical data in files

### Future Database Integration
- Market data models support database serialization
- Caching layer can persist to database
- Real-time updates can be stored efficiently

## Error Handling

Comprehensive error handling throughout the module:

### Network Errors
- Automatic retries with exponential backoff
- Graceful fallback to alternative sources
- Clear error messages for debugging

### Data Quality
- Validation of fetched data
- Detection of incomplete or corrupted data
- Fallback to cached data when available

### Logging
- Detailed logging of all data fetching attempts
- Performance metrics for optimization
- Error tracking for reliability monitoring

## Configuration

Market data behavior can be configured through settings:

```json
{
  "market_data": {
    "primary_source": "yahoo",
    "enable_fallbacks": true,
    "cache_duration_minutes": 15,
    "max_retries": 3,
    "timeout_seconds": 30
  }
}
```

## Performance Considerations

### Caching Strategy
- Aggressive caching during market hours
- Longer cache duration after market close
- Memory-efficient cache management

### Batch Operations
- Support for fetching multiple symbols at once
- Optimized API calls to reduce latency
- Parallel fetching where supported

### Rate Limiting
- Respect API rate limits
- Automatic throttling when needed
- Queue management for high-volume requests

## Future Enhancements

Planned improvements for database migration:
- Real-time price streaming
- Historical data storage in database
- Advanced caching strategies
- WebSocket support for live updates
- Multi-exchange support