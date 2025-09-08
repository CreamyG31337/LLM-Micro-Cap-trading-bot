#!/usr/bin/env python3
"""Debug script to test instructions printing"""

import pandas as pd
from trading_script import daily_results

# Create empty portfolio
df = pd.DataFrame(columns=['ticker', 'shares', 'stop_loss', 'buy_price', 'cost_basis'])

print("=== TESTING DAILY_RESULTS FUNCTION ===")
print("About to call daily_results...")

try:
    daily_results(df, 289.05)
    print("daily_results completed successfully")
except Exception as e:
    print(f"Exception in daily_results: {e}")
    import traceback
    traceback.print_exc()

print("=== END OF TEST ===")
