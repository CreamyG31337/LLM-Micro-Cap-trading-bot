# Data Integrity Principles

This document outlines the critical data integrity principles that prevent silent data corruption in the trading bot.

## The Problem: Silent Data Corruption

The trading bot was experiencing a critical bug where:
- Portfolio graphs showed "0.00%" performance despite significant drawdowns
- Current prices were silently falling back to average prices when market data couldn't be fetched
- This created the illusion of no P&L when there were actually significant losses

## Root Cause Analysis

The issue was caused by **fallback mechanisms** that silently used stale data:

1. **Price Service Fallbacks**: When current market prices couldn't be fetched, the system would use:
   - Previous day's close prices
   - Average cost basis prices
   - Any existing "current price" from the database

2. **Silent Data Insertion**: These fallback prices were saved to the database without any indication that they were stale, leading to:
   - `Current Price = Average Price` for all positions
   - P&L calculations showing near-zero values
   - Incorrect portfolio performance displays

## The Solution: Fail-Hard Philosophy

We implemented a **fail-hard approach** with the following principles:

### 1. No Fallback Prices
```python
# ❌ NEVER DO THIS - Silent data corruption
if current_price is None:
    current_price = avg_price  # This corrupts data!

# ✅ DO THIS - Fail clearly
if current_price is None:
    raise Exception(f"Price fetch failed for {ticker} - aborting snapshot creation")
```

### 2. Data Quality Verification
Before including today's data in graphs, verify that current prices differ from average prices:
```python
# Check for real market data vs stale data
diff = abs(row['Current Price'] - row['Average Price'])
if diff > 0.01:  # Real market data should have differences
    has_real_prices = True
```

### 3. Clear Error Messages
When price fetches fail, provide specific error messages:
```python
print_error(f"❌ CRITICAL: Price fetch failed for {ticker}")
print_error(f"   Cannot create snapshot without valid market prices")
print_error(f"   NO FALLBACK PRICES ALLOWED - data integrity is critical")
```

## Implementation Details

### Portfolio Rebuild Script (`debug/rebuild_portfolio_complete.py`)
- **Position Filtering**: Only include positions with shares > 0
- **Price Validation**: Fail hard if any position can't fetch current prices
- **Clear Logging**: Show exactly how many positions were filtered and why

### Price Service (`utils/price_service.py`)
- **No Fallbacks**: Skip positions entirely if price fetch fails
- **Data Integrity**: Never use old prices, average prices, or any fallback data
- **Clear Logging**: Explain why positions are excluded

### Graph Generator (`Scripts and CSV Files/Generate_Graph.py`)
- **Data Quality Check**: Verify real market data before including today
- **Smart Inclusion**: Include today if real prices are available
- **Weekend Handling**: Forward-fill data for weekends/holidays

## Benefits

1. **Data Integrity**: No silent corruption of portfolio data
2. **Clear Failures**: System fails loudly when data can't be fetched
3. **Accurate P&L**: Real market prices ensure correct performance calculations
4. **Debugging**: Clear error messages make issues easy to identify

## When Failures Occur

The system will fail in these scenarios:
- **Non-trading days**: Trying to fetch prices on weekends/holidays
- **Network issues**: API failures or connectivity problems
- **Invalid tickers**: Symbols that don't exist or are delisted

**This is intentional and correct behavior.** It's better to fail clearly than to silently insert garbage data.

## Monitoring

Watch for these log messages that indicate data integrity issues:
- `"Price fetch failed for {ticker}"` - API/network issues
- `"data appears stale"` - Current prices equal average prices
- `"Filtered out {ticker}: 0 shares"` - Normal position filtering

## Best Practices

1. **Never use fallback prices** - Always fail hard when prices can't be fetched
2. **Verify data quality** - Check that current prices differ from average prices
3. **Clear error messages** - Make failures obvious and actionable
4. **Log everything** - Track what positions are filtered and why
5. **Test on trading days** - Avoid running price fetches on weekends/holidays

This approach ensures that the trading bot maintains data integrity and provides accurate portfolio performance information.
