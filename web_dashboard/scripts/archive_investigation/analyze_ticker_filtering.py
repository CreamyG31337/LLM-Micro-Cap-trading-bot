"""
Analysis: What tickers are being filtered out?

Current rule: Ticker must match ^[A-Z]{1,5}$

This rejects:
- Options (AAPL250117C00150000)
- Bonds (US10Y, TIPS, etc.)
- 6+ character tickers
- Tickers with numbers or special chars
- Tickers with dots (BRK.B, BF.B)

The 7k gap breakdown:
- 508 explicitly skipped (no ticker field)
- ~6,400 rejected by ticker validation regex

Recommendation: Relax the validation to allow:
1. Longer tickers (up to 10 chars)
2. Numbers in tickers
3. Dots for share classes (BRK.B)

New proposed regex: ^[A-Z0-9\\.]{1,10}$

This would capture:
- Standard stocks: AAPL, MSFT (current ✓)
- Share classes: BRK.B, BF.A (currently ✗)
- Longer tickers: ARKK, SPXL (currently ✓ if ≤5 chars)
- With numbers: BTC2 (currently ✗)

Still excludes full option strings which are 20+ chars.
"""

import sys
sys.path.insert(0, 'web_dashboard')

# Test the current vs proposed regex
import re

test_tickers = [
    "AAPL",      # Standard - should pass both
    "MSFT",      # Standard - should pass both
    "BRK.B",     # Share class - FAILS current, PASSES new
    "GOOGL",     # Standard - should pass both
    "SPY",       # Standard - should pass both
    "ARKK",      # 4 chars - should pass both
    "TSLA", # Standard - should pass both
    "BTC2L",     # With number - FAILS current, PASSES new
    "US10Y",     # Bond - FAILS current, PASSES new
    "AAPL250117C00150000",  # Option - FAILS both
]

current_pattern = r'^[A-Z]{1,5}$'
proposed_pattern = r'^[A-Z0-9\\.]{1,10}$'

print("Ticker Validation Comparison:")
print("="*60)
print(f"{'Ticker':<25} | Current | Proposed")
print("-"*60)

for ticker in test_tickers:
    current_match = bool(re.match(current_pattern, ticker))
    proposed_match = bool(re.match(proposed_pattern, ticker))
    
    status_current = "✓" if current_match else "✗"
    status_proposed = "✓" if proposed_match else "✗"
    
    print(f"{ticker:<25} | {status_current:^7} | {status_proposed:^8}")

print("\nRecommendation: Update regex to capture more valid tickers")
