#!/usr/bin/env python3
"""Find all positions across all funds, including CTRN and NUE"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

print("="*80)
print("Searching ALL funds for CTRN and NUE")
print("="*80)

# Search latest_positions for CTRN
print("\nSearching for CTRN in latest_positions:")
ctrn_result = client.supabase.table('latest_positions')\
    .select('*')\
    .eq('ticker', 'CTRN')\
    .execute()

if ctrn_result.data:
    print(f"Found {len(ctrn_result.data)} CTRN positions:")
    for row in ctrn_result.data:
        print(f"  Fund: {row.get('fund', 'UNKNOWN')}")
        print(f"  Shares: {row.get('shares', 0)}")
        print(f"  Price: ${row.get('current_price', 0) or row.get('price', 0):.2f}")
        print(f"  Cost Basis: ${row.get('cost_basis', 0):.2f}")
        print(f"  Market Value: ${row.get('market_value', 0):.2f}")
        print(f"  Unrealized P&L: ${row.get('unrealized_pnl', 0):.2f}")
        print(f"  Currency: {row.get('currency', 'UNKNOWN')}")
        print()
else:
    print("  CTRN not found in latest_positions")

# Search latest_positions for NUE
print("\nSearching for NUE in latest_positions:")
nue_result = client.supabase.table('latest_positions')\
    .select('*')\
    .eq('ticker', 'NUE')\
    .execute()

if nue_result.data:
    print(f"Found {len(nue_result.data)} NUE positions:")
    for row in nue_result.data:
        print(f"  Fund: {row.get('fund', 'UNKNOWN')}")
        print(f"  Shares: {row.get('shares', 0)}")
        print(f"  Price: ${row.get('current_price', 0) or row.get('price', 0):.2f}")
        print(f"  Cost Basis: ${row.get('cost_basis', 0):.2f}")
        print(f"  Market Value: ${row.get('market_value', 0):.2f}")
        print(f"  Unrealized P&L: ${row.get('unrealized_pnl', 0):.2f}")
        print(f"  Currency: {row.get('currency', 'UNKNOWN')}")
        print()
else:
    print("  NUE not found in latest_positions")

# Also check portfolio_positions directly
print("\n" + "="*80)
print("Checking portfolio_positions table directly:")
print("="*80)

# Get all positions and group by fund
all_positions = client.supabase.table('portfolio_positions')\
    .select('fund, ticker, shares, price, cost_basis, currency, date')\
    .order('date', desc=True)\
    .limit(10000)\
    .execute()

if all_positions.data:
    df = pd.DataFrame(all_positions.data)
    
    # Check for CTRN
    ctrn_positions = df[df['ticker'] == 'CTRN']
    if len(ctrn_positions) > 0:
        print(f"\nFound {len(ctrn_positions)} CTRN records in portfolio_positions:")
        for fund in ctrn_positions['fund'].unique():
            fund_pos = ctrn_positions[ctrn_positions['fund'] == fund].sort_values('date', ascending=False)
            latest = fund_pos.iloc[0]
            print(f"  Fund: {fund}")
            print(f"  Latest: Shares={latest['shares']}, Price=${latest['price']:.2f}, Cost=${latest['cost_basis']:.2f}, Currency={latest['currency']}")
            market_value = float(latest['shares']) * float(latest['price'])
            pnl = market_value - float(latest['cost_basis'])
            print(f"  Calculated: Market Value=${market_value:.2f}, P&L=${pnl:.2f}")
    else:
        print("  CTRN not found in portfolio_positions")
    
    # Check for NUE
    nue_positions = df[df['ticker'] == 'NUE']
    if len(nue_positions) > 0:
        print(f"\nFound {len(nue_positions)} NUE records in portfolio_positions:")
        for fund in nue_positions['fund'].unique():
            fund_pos = nue_positions[nue_positions['fund'] == fund].sort_values('date', ascending=False)
            latest = fund_pos.iloc[0]
            print(f"  Fund: {fund}")
            print(f"  Latest: Shares={latest['shares']}, Price=${latest['price']:.2f}, Cost=${latest['cost_basis']:.2f}, Currency={latest['currency']}")
            market_value = float(latest['shares']) * float(latest['price'])
            pnl = market_value - float(latest['cost_basis'])
            print(f"  Calculated: Market Value=${market_value:.2f}, P&L=${pnl:.2f}")
    else:
        print("  NUE not found in portfolio_positions")
    
    # List all unique funds
    print(f"\n{'='*80}")
    print("All funds in database:")
    print(f"{'='*80}")
    for fund in sorted(df['fund'].unique()):
        fund_positions = df[df['fund'] == fund]
        unique_tickers = fund_positions['ticker'].unique()
        print(f"  {fund}: {len(unique_tickers)} unique tickers")
        if 'CTRN' in unique_tickers or 'NUE' in unique_tickers:
            print(f"    *** Contains CTRN or NUE! ***")

