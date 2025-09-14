# Test Data - Safe Testing Environment

This folder contains **test copies** of your trading data for safe development and testing.

## What's Here

- `llm_portfolio_update.csv` - Test copy of your portfolio (safe to modify)
- `llm_trade_log.csv` - Test copy of your trade history (safe to modify)  
- `cash_balances.json` - Test copy of cash balances (safe to modify)

## How to Use

### For Testing/Development:
```bash
# Use test data folder
python trading_script.py --data-dir test_data

# Or with specific file
python trading_script.py --file test_data/llm_portfolio_update.csv --data-dir test_data
```

### For Production Trading:
```bash
# Use production data (default)
python trading_script.py

# Or explicitly specify production folder
python trading_script.py --data-dir "my trading"
```

## Important Notes

- ✅ **Safe to modify**: These are copies - experiment freely!
- 🔄 **Refresh when needed**: Copy fresh data from `my trading/` folder when you want current data
- 🚫 **Never use for real trading**: Always switch to production folder for actual trades
- 📝 **Test new features**: Perfect for testing new functionality without risking production data

## Refreshing Test Data

To get fresh copies from production:
```bash
copy "my trading\*.csv" "test_data\"
copy "my trading\*.json" "test_data\"
```

---

*Test environment created for safe LLM Micro-Cap Trading Bot development.*
