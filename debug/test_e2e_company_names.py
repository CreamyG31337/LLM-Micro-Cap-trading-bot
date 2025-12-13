#!/usr/bin/env python3
"""Test end-to-end trade log with company names"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test full flow through streamlit_utils
from web_dashboard.streamlit_utils import get_trade_log

print("Testing streamlit_utils.get_trade_log (full flow):")
print("=" * 60)

# Get trades for Chimera
trades_df = get_trade_log(limit=20, fund="Project Chimera")
print(f"Chimera fund: {len(trades_df)} trades")

if not trades_df.empty:
    print("\nColumns:", trades_df.columns.tolist())
    print("\n'company_name' column present:", 'company_name' in trades_df.columns)
    
    # Show specific tickers
    for ticker in ['CTRN', 'HLIT.TO']:
        ticker_trades = trades_df[trades_df['ticker'] == ticker]
        if not ticker_trades.empty:
            company = ticker_trades.iloc[0].get('company_name', 'NOT FOUND')
            print(f"{ticker}: {company}")

# Get trades for Webull
print("\n" + "=" * 60)
trades_df2 = get_trade_log(limit=20, fund="RRSP Lance Webull")
print(f"Webull fund: {len(trades_df2)} trades")

if not trades_df2.empty:
    for ticker in ['FDS', 'TSCO']:
        ticker_trades = trades_df2[trades_df2['ticker'] == ticker]
        if not ticker_trades.empty:
            company = ticker_trades.iloc[0].get('company_name', 'NOT FOUND')
            print(f"{ticker}: {company}")

print("\nDone!")
