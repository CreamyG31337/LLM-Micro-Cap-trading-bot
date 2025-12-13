# Backfill Securities Utility

One-time utility to populate the `securities` table with company names and metadata from yfinance for all existing tickers.

## Purpose

Fixes missing company names for tickers that were traded before the auto-population feature was implemented.

## Usage

### Dry Run (Recommended First)

See what would be updated without making changes:

```powershell
python debug/backfill_securities.py --dry-run
```

### Actual Run

Populate the securities table:

```powershell
python debug/backfill_securities.py
```

You'll be prompted to confirm before any changes are made.

## What It Does

1. Scans `portfolio_positions` and `trade_log` for all unique tickers
2. Checks which tickers are missing from `securities` or have NULL/Unknown company names
3. Fetches metadata from yfinance for each missing ticker:
   - Company name (longName or shortName)
   - Sector
   - Industry
   - Country
   - Market cap
4. Inserts/updates the `securities` table

## Output

Shows progress for each ticker:
```
[1/50] Processing AAPL (USD)...
   ✅ Success

[2/50] Processing SHOP.TO (CAD)...
   ✅ Success
```

Final summary:
```
✅ Successful: 48
❌ Errors: 2
📈 Total: 50
```

## Notes

- **One-time use**: After running this once, the auto-population feature handles all future trades
- **Safe**: Won't re-fetch tickers that already have valid company names
- **Requires**: Service role access (uses SUPABASE_SECRET_KEY from .env)
- **Rate limiting**: yfinance may rate-limit if processing many tickers, script will continue past errors

## After Running

All historical positions (including sold ones) should now have company names visible in views like `latest_positions`.
