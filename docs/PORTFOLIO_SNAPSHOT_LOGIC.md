# Portfolio Snapshot Logic

This document explains the logic for creating and updating portfolio snapshots in the LLM Micro-Cap Trading Bot.

## Core Principle: "Get data whenever we can"

The system should always try to create or update portfolio snapshots when possible. The only valid reasons to skip are:

1. **Not a trading day** (weekend/holiday) - No market data available
2. **Already have market close data** - We have the "final" snapshot for the day

## When to Create Snapshots

### ✅ Always Create When:
- Today is a trading day AND we don't have a market close snapshot (16:00)
- We have an intraday snapshot but market is now closed (replace with market close data)
- We're backfilling missing historical data
- We're rebuilding portfolio from scratch

### ❌ Skip Only When:
- Today is not a trading day (weekend/holiday)
- We already have a market close snapshot (16:00) for today

## Snapshot Replacement Rules

### ONE Snapshot Per Day
- Repository layer enforces this - no duplicates allowed
- `save_portfolio_snapshot()` replaces existing data for the same day
- `update_daily_portfolio_snapshot()` updates existing snapshot

### Replacement Logic
- **Intraday snapshots (before 16:00)** → CAN be replaced with market close data
- **Market close snapshots (16:00)** → Should NOT be replaced with earlier intraday data
- **Market close snapshots (16:00)** → CAN be replaced with updated market close data

## Timestamp Rules

### Market Open (9:30 AM - 4:00 PM EST)
- Use current time for intraday snapshots
- Can be overwritten later with market close snapshot

### Market Closed (After 4:00 PM EST)
- Use market close time in user's timezone (4:00 PM EST = 1:00 PM PST) for final snapshots
- This is the "official" end-of-day data we want to keep
- All timestamps stored with timezone information for proper conversion

## When `is_market_open()` Should Be Used

### ✅ Correct Usage:
- **Timestamp decisions**: Use 16:00 if closed, current time if open
- **Check existing data**: See if we already have market close snapshot
- **Avoid overwriting**: Don't replace market close with intraday data

### ❌ Incorrect Usage:
- **Skip creation**: Don't skip creating snapshots just because market is closed
- **Skip fetching**: Don't skip fetching data just because market is closed
- **Skip updates**: Don't skip updates just because market is closed

## Centralized Code Path

### All Portfolio Updates MUST Use:
1. **`utils/portfolio_update_logic.py`** - Core decision logic
2. **`utils/portfolio_refresh.py`** - Refresh function using update logic

### Entry Points That Use Centralized Logic:
- ✅ `trading_script.py` - Main trading interface
- ✅ `Scripts and CSV Files/Generate_Graph.py` - Graph generation
- ✅ `debug/rebuild_portfolio_complete.py` - Portfolio rebuild (FIXED)

### Common Mistakes:
- ❌ Custom logic in debug/rebuild scripts
- ❌ Checking `is_market_open()` to decide whether to skip
- ❌ Different behavior across entry points

## Examples

### Scenario 1: Friday 5:00 PM (Market Closed)
```
Today is a trading day ✓
Market is closed ✓
No existing snapshot → CREATE with 16:00 timestamp
```

### Scenario 2: Friday 5:00 PM (Market Closed, Has Intraday Data)
```
Today is a trading day ✓
Market is closed ✓
Has intraday snapshot (10:00 AM) → UPDATE with 16:00 timestamp
```

### Scenario 3: Friday 5:00 PM (Market Closed, Has Market Close Data)
```
Today is a trading day ✓
Market is closed ✓
Has market close snapshot (16:00) → SKIP (we have what we need)
```

### Scenario 4: Saturday (Weekend)
```
Today is not a trading day → SKIP (no market data available)
```

### Scenario 5: Monday 2:00 PM (Market Open)
```
Today is a trading day ✓
Market is open ✓
No existing snapshot → CREATE with current timestamp
```

## Implementation Details

### Repository Layer Protection
- `save_portfolio_snapshot()` - Replaces existing data for same day
- `update_daily_portfolio_snapshot()` - Updates existing snapshot
- Protection against overwriting market close (16:00) with earlier data

### Market Hours Integration
- `MarketHours.is_trading_day()` - Check if it's a trading day
- `MarketHours.is_market_open()` - Check if market is currently open
- Use for timestamp decisions, not for skipping operations

### Error Handling
- Graceful handling of missing data
- Clear error messages for debugging
- Automatic retry for transient failures

## Debugging

### Common Issues:
1. **"Skipping final snapshot - market is closed"** - Wrong! Should check if we have data
2. **Duplicate snapshots** - Repository should prevent this
3. **Inconsistent behavior** - All entry points should use same logic

### Debug Commands:
```bash
# Check if portfolio needs update
python -c "
from utils.portfolio_update_logic import should_update_portfolio
from market_data.market_hours import MarketHours
from portfolio.portfolio_manager import PortfolioManager
# ... check logic
"

# Test rebuild script
python debug/rebuild_portfolio_complete.py --data-dir "trading_data/funds/TEST"
```

## Best Practices

1. **Always use centralized logic** - Don't implement custom update logic
2. **Test all entry points** - Ensure consistent behavior
3. **Document decisions** - Explain why certain logic exists
4. **Handle edge cases** - Weekends, holidays, missing data
5. **Monitor for duplicates** - Repository layer should prevent this

## Related Files

- `utils/portfolio_update_logic.py` - Core decision logic
- `utils/portfolio_refresh.py` - Refresh implementation
- `debug/rebuild_portfolio_complete.py` - Portfolio rebuild
- `data/repositories/` - Repository layer protection
- `market_data/market_hours.py` - Market timing utilities
