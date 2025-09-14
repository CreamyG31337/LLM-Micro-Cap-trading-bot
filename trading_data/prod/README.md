# My Trading - Private Data Folder

This folder contains your **private trading data** and is excluded from version control.

## What's Stored Here

- `llm_portfolio_update.csv` - Your current portfolio positions and performance
- `llm_trade_log.csv` - Complete history of all your trades
- Any other personal trading data files

## Privacy & Security

- ✅ **Git Ignored**: This entire folder is in `.gitignore` so your trading data stays private
- ✅ **Local Only**: These files never get committed to GitHub or shared publicly
- ✅ **Default Location**: The trading scripts now use this folder by default

## Getting Started

1. **First Time Setup**: The folder is created automatically when you run the trading script
2. **Default Usage**: Simply run `python trading_script.py` (no --file parameter needed)
3. **Your Data**: All CSV files will be saved here automatically

## File Structure

```
my trading/
├── README.md                    # This file
├── llm_portfolio_update.csv     # Your portfolio (created when you start trading)
└── llm_trade_log.csv           # Your trade history (created when you make trades)
```

## Important Notes

- **Keep this folder secure** - it contains your real trading data
- **Backup regularly** - consider backing up your CSV files separately
- **Don't share** - never commit or share files from this folder

---

*This folder was automatically created by the LLM Micro-Cap Trading Bot system.*
