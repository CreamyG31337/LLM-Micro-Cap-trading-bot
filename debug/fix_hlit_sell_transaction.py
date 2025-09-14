#!/usr/bin/env python3
"""
Fix HLIT.TO Sell Transaction
This script properly processes the HLIT.TO sell transaction from the trade log
and updates the portfolio to show the correct sell action and remaining shares.
"""

import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_hlit_sell_transaction():
    """Fix HLIT.TO sell transaction processing."""
    
    print("🔧 Fixing HLIT.TO Sell Transaction Processing")
    print("=" * 60)
    
    # Load data files
    portfolio_file = Path("my trading/llm_portfolio_update.csv")
    trade_log_file = Path("my trading/llm_trade_log.csv")
    
    if not portfolio_file.exists():
        print("❌ Portfolio file not found")
        return False
    
    if not trade_log_file.exists():
        print("❌ Trade log file not found")
        return False
    
    # Read files
    portfolio_df = pd.read_csv(portfolio_file)
    trade_df = pd.read_csv(trade_log_file)
    
    print(f"📊 Loaded portfolio with {len(portfolio_df)} records")
    print(f"📊 Loaded trade log with {len(trade_df)} records")
    
    # Find HLIT.TO trades
    hlit_trades = trade_df[trade_df['Ticker'] == 'HLIT.TO']
    print(f"\n🔍 HLIT.TO trades found: {len(hlit_trades)}")
    
    for _, trade in hlit_trades.iterrows():
        print(f"   {trade['Date']} - {trade['Reason']} - {trade['Shares']} shares @ ${trade['Price']}")
    
    # Process HLIT.TO trades to calculate net position
    total_shares = 0
    total_cost = 0
    sell_shares = 0
    sell_price = 0
    
    for _, trade in trade_df.iterrows():
        if trade['Ticker'] == 'HLIT.TO':
            shares = float(trade['Shares'])
            price = float(trade['Price'])
            cost = float(trade['Cost Basis'])
            reason = trade['Reason']
            
            if 'BUY' in reason.upper():
                total_shares += shares
                total_cost += cost
                print(f"   📈 BUY: +{shares} shares @ ${price} = ${cost}")
            elif 'SELL' in reason.upper() or 'sell' in reason.lower():
                sell_shares = shares
                sell_price = price
                print(f"   📉 SELL: -{shares} shares @ ${price}")
    
    # Calculate net position
    net_shares = total_shares - sell_shares
    net_cost = total_cost - (sell_shares * sell_price) if sell_shares > 0 else total_cost
    
    print(f"\n📊 HLIT.TO Position Summary:")
    print(f"   Total bought: {total_shares} shares, ${total_cost:.2f}")
    print(f"   Total sold: {sell_shares} shares @ ${sell_price}")
    print(f"   Net position: {net_shares} shares, ${net_cost:.2f}")
    
    # Find the latest HLIT.TO entry in portfolio
    hlit_portfolio = portfolio_df[portfolio_df['Ticker'] == 'HLIT.TO']
    if hlit_portfolio.empty:
        print("❌ No HLIT.TO entries found in portfolio")
        return False
    
    latest_hlit_idx = hlit_portfolio.index[-1]
    latest_hlit = hlit_portfolio.iloc[-1]
    
    print(f"\n🔍 Latest HLIT.TO portfolio entry:")
    print(f"   Date: {latest_hlit['Date']}")
    print(f"   Shares: {latest_hlit['Shares']}")
    print(f"   Action: {latest_hlit['Action']}")
    
    # Update the latest HLIT.TO entry
    if sell_shares > 0:
        # If there was a sell, update to show sell action and correct shares
        portfolio_df.at[latest_hlit_idx, 'Shares'] = net_shares
        portfolio_df.at[latest_hlit_idx, 'Average Price'] = round(net_cost / net_shares, 2) if net_shares > 0 else 0
        portfolio_df.at[latest_hlit_idx, 'Cost Basis'] = round(net_cost, 2)
        portfolio_df.at[latest_hlit_idx, 'Action'] = 'SELL'
        portfolio_df.at[latest_hlit_idx, 'Current Price'] = sell_price
        portfolio_df.at[latest_hlit_idx, 'Total Value'] = round(net_shares * sell_price, 2)
        portfolio_df.at[latest_hlit_idx, 'PnL'] = round((sell_price - (net_cost / net_shares)) * net_shares, 2) if net_shares > 0 else 0
        
        print(f"\n✅ Updated HLIT.TO entry:")
        print(f"   Shares: {latest_hlit['Shares']} → {net_shares}")
        print(f"   Action: {latest_hlit['Action']} → SELL")
        print(f"   Current Price: {latest_hlit['Current Price']} → {sell_price}")
        print(f"   PnL: {latest_hlit['PnL']} → {round((sell_price - (net_cost / net_shares)) * net_shares, 2) if net_shares > 0 else 0}")
    else:
        print("✅ No sell transaction found - keeping current position")
    
    # Save updated portfolio
    portfolio_df.to_csv(portfolio_file, index=False)
    print(f"\n💾 Updated portfolio saved to: {portfolio_file}")
    
    return True

if __name__ == "__main__":
    success = fix_hlit_sell_transaction()
    sys.exit(0 if success else 1)
