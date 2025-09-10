# Debug Tools for LLM Micro-Cap Trading Bot

This folder contains debugging and utility scripts for the trading bot.

## ⚠️ Important: Always Activate Virtual Environment First!

Before running any Python scripts in this project, always activate the virtual environment:

### Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

### Windows (Command Prompt):
```cmd
.\venv\Scripts\activate.bat
```

### Or use the convenience script:
```cmd
debug\activate_venv.bat
```

## Available Debug Scripts

### 1. `comprehensive_price_debug.py`
Main debugging tool for price data issues.

**Usage:**
```bash
# Debug single ticker
python debug/comprehensive_price_debug.py VEE.TO

# Debug multiple tickers
python debug/comprehensive_price_debug.py --multi VEE.TO GMIN.TO

# Quiet mode for scripting
python debug/comprehensive_price_debug.py VEE.TO --quiet
```

### 2. `price_debug.py`
Simple debug script specifically for VEE.TO price data.

### 3. `gmin_debug.py`
Quick debug script for GMIN.TO price data.

### 4. `recalculate_portfolio_data.py`
Comprehensive script that recalculates ALL portfolio data (shares, prices, cost basis) based on the trade log data.

**Usage:**
```bash
# Recalculate all data for default data directory
python debug/recalculate_portfolio_data.py

# Recalculate all data for specific data directory
python debug/recalculate_portfolio_data.py test_data
```

**When to use:**
- After manually editing the trade log
- When portfolio CSV has stale data (shares, prices, or cost basis)
- To verify all calculations are correct
- When you notice share count discrepancies
- To sync portfolio CSV with trade log after manual edits

**What it fixes:**
- Share count discrepancies (e.g., 3.0 vs 3.1406 shares)
- Average price calculations
- Cost basis calculations
- Any data inconsistencies between trade log and portfolio

### 5. `activate_venv.bat`
Convenience script to activate the virtual environment.

## Common Issues and Solutions

### "No module named 'yfinance'" or similar errors
- **Solution**: Always activate the virtual environment first using the commands above.

### Price data discrepancies
- Use `comprehensive_price_debug.py` to compare Yahoo Finance data with portfolio records
- Check for backdated prices (using current price for historical dates)
- Verify previous close vs current price usage

### Missing data ("NO DATA" entries)
- Run the main trading script to fetch current data
- Use debug scripts to verify data accuracy
- Manually correct historical data if needed

## ⚠️ Known Issues Requiring Manual Monitoring

### Corporate Actions (Stock Splits & Dividend Reinvestments)
**Issue**: Wealthsimple automatically handles stock splits and dividend reinvestments, but these events are not captured in the trade log, causing discrepancies between the bot's records and actual holdings.

**Examples**:
- **Stock Split**: CRWD 2:1 split → 0.7261 shares becomes 1.4522 shares
- **Dividend Reinvestment**: CRWD pays $0.50 dividend → automatically reinvested as additional fractional shares
- **Mixed Holdings**: Personal + Bot holdings in same TFSA account make tracking complex

**Current Workaround**:
- Monitor Wealthsimple emails for corporate action notifications
- Manually adjust portfolio CSV when discrepancies are detected
- Use `recalculate_portfolio_data.py` to sync data after manual corrections

**Future Solutions** (TODO):
- Create manual correction tool for corporate actions
- Integrate with Wealthsimple data export
- Implement corporate actions database
- Add automatic detection and adjustment

**Monitoring Required**:
- Check share counts against Wealthsimple holdings regularly
- Watch for unexpected changes in total share counts
- Verify cost basis calculations after corporate actions
- Keep trade log and portfolio CSV synchronized

## Best Practices

1. **Always activate venv first** - This is the most common source of errors
2. **Use test data for development** - Run with `--data-dir test_data` flag
3. **Verify price data accuracy** - Use debug scripts before making corrections
4. **Keep debug scripts updated** - Add new tickers or features as needed
