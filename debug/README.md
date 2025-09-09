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

### 4. `activate_venv.bat`
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

## Best Practices

1. **Always activate venv first** - This is the most common source of errors
2. **Use test data for development** - Run with `--data-dir test_data` flag
3. **Verify price data accuracy** - Use debug scripts before making corrections
4. **Keep debug scripts updated** - Add new tickers or features as needed
